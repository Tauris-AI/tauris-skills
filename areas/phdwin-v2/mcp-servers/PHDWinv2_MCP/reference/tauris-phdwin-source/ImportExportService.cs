using System.IO.Compression;
using System.Data;
using System.Data.Odbc;
using System.Text;
using System.Text.Json;
using Dapper;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Npgsql;
using Tauris.Odbc.Common.Objects.AriesEntities;
using Tauris.PhdWin.Server.Endpoints.Aries;
using Tauris.Odbc.Objects;
using LookupRow = Tauris.PhdWin.Server.Endpoints.Aries.AriesLookupRepository.LookupRow;
using ScenarioRow = Tauris.PhdWin.Server.Endpoints.Aries.ScenarioEntity;
using SetupDataEntity = Tauris.PhdWin.Server.Endpoints.ModelVariable.SetupDataEntity;

namespace Tauris.PhdWin.Server.Endpoints.Imports;

public interface IImportExportService
{
    Task<ImportExportResult> GenerateAsync(Guid jobId, ImportExportRequest request, CancellationToken cancellationToken = default);
    string GetExportPath(Guid jobId, Guid exportId);
}

public sealed class ImportExportService : IImportExportService
{
    private const int AccessExportColumnCount = 255;
    private const int AccessInsertBatchSize = 250;
    private const int AccessTransactionBatchSize = 5000;
    private const long AccessRecommendedMaxBytes = 2L * 1024 * 1024 * 1024;

    private readonly ImportStorageOptions _storageOptions;
    private readonly PostgresImportOptions _postgresOptions;
    private readonly IImportJobService _importJobService;
    private readonly IImportTemplateService _importTemplateService;
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly IServiceProvider _serviceProvider;

    public ImportExportService(
        IOptions<ImportStorageOptions> storageOptions,
        IOptions<PostgresImportOptions> postgresOptions,
        IImportJobService importJobService,
        IHttpContextAccessor httpContextAccessor,
        IServiceProvider serviceProvider,
        IImportTemplateService importTemplateService)
    {
        _storageOptions = storageOptions.Value;
        _postgresOptions = postgresOptions.Value;
        _importJobService = importJobService;
        _httpContextAccessor = httpContextAccessor;
        _importTemplateService = importTemplateService;
        _serviceProvider = serviceProvider;
    }

    public async Task<ImportExportResult> GenerateAsync(Guid jobId, ImportExportRequest request, CancellationToken cancellationToken = default)
    {
        var job = await _importJobService.GetAsync(jobId, cancellationToken)
                  ?? throw new InvalidOperationException($"Import job {jobId} was not found.");

        try
        {
            job.Status = ImportJobStatus.Exporting;
            job.UpdatedAtUtc = DateTime.UtcNow;
            job.AddExportMessage("Export generation started.");
            await _importJobService.SaveAsync(job, cancellationToken);

            var exportId = Guid.NewGuid();
            var exportRoot = GetExportPath(jobId, exportId);
            var filesRoot = Path.Combine(exportRoot, "files");
            Directory.CreateDirectory(filesRoot);

            var result = new ImportExportResult
            {
                ExportId = exportId,
                JobId = jobId,
                CreatedAtUtc = DateTime.UtcNow
            };
            var exportBaseFileName = BuildExportBaseFileName(job, result.CreatedAtUtc);

            var normalizedFormats = request.Formats.Count == 0
                ? new HashSet<string>(new[] { "csv" }, StringComparer.OrdinalIgnoreCase)
                : new HashSet<string>(request.Formats.Where(f => !string.IsNullOrWhiteSpace(f)).Select(f => f.Trim()), StringComparer.OrdinalIgnoreCase);
            var exportPresetKey = string.IsNullOrWhiteSpace(request.ExportPresetKey)
                ? "all_data"
                : request.ExportPresetKey.Trim();
            var generatedAnyFiles = false;
            var requestedTables = request.AllTables || request.SelectedTables.Count == 0
                ? null
                : request.SelectedTables.Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(name => name).ToList();
            var selectedTableMetadata = await LoadSelectedTableMetadataAsync(job, requestedTables, result, cancellationToken);

            var accessExportPlan = BuildAccessExportPlan(normalizedFormats, selectedTableMetadata);
            result.AccessExportPlan = accessExportPlan;
            AddAccessWarnings(accessExportPlan, result);

            if (string.Equals(exportPresetKey, "aries_bundle", StringComparison.OrdinalIgnoreCase))
            {
                await GenerateAriesBundleAsync(job, request, filesRoot, result, cancellationToken);
                generatedAnyFiles = result.GeneratedFiles.Count > 0;
                normalizedFormats.Add("json");
                if (request.SelectedTables.Count > 0 || !request.AllTables)
                {
                    result.Warnings.Add("SelectedTables and AllTables are ignored for Aries bundle export. Use LeaseIds to choose lease-specific bundle output.");
                }
            }

            if (!string.Equals(exportPresetKey, "aries_bundle", StringComparison.OrdinalIgnoreCase) && normalizedFormats.Contains("csv"))
            {
                if (!string.Equals(exportPresetKey, "all_data", StringComparison.OrdinalIgnoreCase))
                {
                    await GenerateExposureCsvAsync(job, exportPresetKey, filesRoot, result, cancellationToken);
                }
                else
                {
                    var usePostgres = !string.IsNullOrWhiteSpace(_postgresOptions.ConnectionString);
                    if (!usePostgres)
                    {
                        var manifest = await LoadWorkspaceManifestAsync(jobId, cancellationToken);
                        var tables = (requestedTables == null
                                ? manifest.Tables
                                    .OrderBy(t => ImportTableNameHelper.GetSourceSortRank(t.SourceKind))
                                    .ThenBy(t => t.LogicalTableName, StringComparer.OrdinalIgnoreCase)
                                : manifest.Tables.Where(t => requestedTables.Contains(t.LogicalTableName, StringComparer.OrdinalIgnoreCase)))
                            .ToList();

                        foreach (var table in tables)
                        {
                            var rows = await LoadWorkspaceRowsAsync(jobId, table.FileName, cancellationToken);
                            var csvPath = Path.Combine(filesRoot, $"{SanitizeFileName(table.LogicalTableName)}.csv");
                            await WriteCsvAsync(csvPath, rows.Select(r => JsonSerializer.Serialize(r)).ToList(), cancellationToken);
                            result.GeneratedFiles.Add(Path.GetFileName(csvPath));
                        }
                    }
                    else
                    {
                        try
                        {
                            await using var connection = new NpgsqlConnection(_postgresOptions.ConnectionString);
                            await connection.OpenAsync(cancellationToken);

                            var manifest = await LoadPostgresManifestAsync(connection, jobId, cancellationToken);
                            var tables = (requestedTables == null
                                    ? manifest
                                        .OrderBy(t => ImportTableNameHelper.GetSourceSortRank(t.SourceKind))
                                        .ThenBy(t => t.LogicalTableName, StringComparer.OrdinalIgnoreCase)
                                    : manifest.Where(t => requestedTables.Contains(t.LogicalTableName, StringComparer.OrdinalIgnoreCase)))
                                .ToList();

                            foreach (var table in tables)
                            {
                                var rows = (await connection.QueryAsync<string>(
                                    $"""
                                    select row_data::text
                                    from {QuoteIdentifier(job.PostgresSchema ?? GetSchemaName(jobId))}.{QuoteIdentifier(table.PostgresTableName!)}
                                    order by row_index;
                                    """)).ToList();

                                var csvPath = Path.Combine(filesRoot, $"{SanitizeFileName(table.LogicalTableName)}.csv");
                                await WriteCsvAsync(csvPath, rows, cancellationToken);
                                result.GeneratedFiles.Add(Path.GetFileName(csvPath));
                            }
                        }
                        catch (NpgsqlException ex)
                        {
                            result.Warnings.Add($"PostgreSQL raw-table export is unavailable ({ex.SqlState ?? "n/a"}). Falling back to staged workspace JSON for CSV generation.");
                            var manifest = await LoadWorkspaceManifestAsync(jobId, cancellationToken);
                            var tables = (requestedTables == null
                                    ? manifest.Tables
                                        .OrderBy(t => ImportTableNameHelper.GetSourceSortRank(t.SourceKind))
                                        .ThenBy(t => t.LogicalTableName, StringComparer.OrdinalIgnoreCase)
                                    : manifest.Tables.Where(t => requestedTables.Contains(t.LogicalTableName, StringComparer.OrdinalIgnoreCase)))
                                .ToList();

                            foreach (var table in tables)
                            {
                                var rows = await LoadWorkspaceRowsAsync(jobId, table.FileName, cancellationToken);
                                var csvPath = Path.Combine(filesRoot, $"{SanitizeFileName(table.LogicalTableName)}.csv");
                                await WriteCsvAsync(csvPath, rows.Select(r => JsonSerializer.Serialize(r)).ToList(), cancellationToken);
                                result.GeneratedFiles.Add(Path.GetFileName(csvPath));
                            }
                        }
                    }
                }
                generatedAnyFiles = result.GeneratedFiles.Count > 0;
            }

            if (normalizedFormats.Contains("phdwin_access"))
            {
                if (!string.Equals(exportPresetKey, "all_data", StringComparison.OrdinalIgnoreCase))
                {
                    result.Warnings.Add("PHDWin Access DB export ignores curated export presets and writes staged tables as-is.");
                }

                await GeneratePhdWinAccessAsync(job, filesRoot, requestedTables, exportBaseFileName, result, cancellationToken);
                generatedAnyFiles = result.GeneratedFiles.Count > 0;
            }

            if (normalizedFormats.Contains("aries_accdb"))
            {
                await GenerateAriesAccessAsync(job, request, filesRoot, exportBaseFileName, result, cancellationToken);
                generatedAnyFiles = result.GeneratedFiles.Count > 0;
            }

            if (accessExportPlan?.Requested == true)
            {
                var accessPlanPath = Path.Combine(filesRoot, "access-export-plan.json");
                await WriteJsonAsync(accessPlanPath, accessExportPlan, cancellationToken);
                result.GeneratedFiles.Add(Path.GetFileName(accessPlanPath));
                generatedAnyFiles = true;
            }

            if (generatedAnyFiles)
            {
                var zipFileName = $"{exportBaseFileName}.zip";
                var zipPath = Path.Combine(exportRoot, zipFileName);
                if (File.Exists(zipPath))
                {
                    File.Delete(zipPath);
                }

                ZipFile.CreateFromDirectory(filesRoot, zipPath);
                result.DownloadPath = Path.GetRelativePath(_storageOptions.RootPath, zipPath).Replace('\\', '/');
            }

            var metadataPath = Path.Combine(exportRoot, "export.json");
            await File.WriteAllTextAsync(metadataPath, JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }), cancellationToken);

            job.Status = ImportJobStatus.Completed;
            job.UpdatedAtUtc = DateTime.UtcNow;
            job.AddExportMessage($"Export package {exportId:N} completed.");
            await _importJobService.SaveAsync(job, cancellationToken);

            return result;
        }
        catch
        {
            job.Status = ImportJobStatus.Failed;
            job.UpdatedAtUtc = DateTime.UtcNow;
            job.AddExportMessage("Export generation failed.");
            await _importJobService.SaveAsync(job, cancellationToken);
            throw;
        }
    }

    public string GetExportPath(Guid jobId, Guid exportId)
    {
        return Path.Combine(_storageOptions.RootPath, "imports", jobId.ToString("N"), "exports", exportId.ToString("N"));
    }

    private async Task GenerateAriesBundleAsync(
        ImportJobRecord job,
        ImportExportRequest request,
        string filesRoot,
        ImportExportResult result,
        CancellationToken cancellationToken)
    {
        var ariesExportBundleService = _serviceProvider.GetRequiredService<IAriesExportBundleService>();

        if (job.SourceKind != ImportSourceKind.PhdWin)
        {
            throw new InvalidOperationException("Aries bundle export is currently supported for PHDWin import jobs only.");
        }

        if (request.LeaseIds.Count == 0)
        {
            throw new InvalidOperationException("Aries bundle export requires at least one lease id.");
        }

        var referenceBundle = await ariesExportBundleService.BuildReferenceBundleAsync();
        var referencePath = Path.Combine(filesRoot, "aries-reference-bundle.json");
        await WriteJsonAsync(referencePath, referenceBundle, cancellationToken);
        result.GeneratedFiles.Add(Path.GetFileName(referencePath));

        foreach (var leaseId in request.LeaseIds.Distinct().OrderBy(x => x))
        {
            var leaseBundle = await ariesExportBundleService.BuildLeaseBundleAsync(leaseId, request.NoSidefile);
            var leasePath = Path.Combine(filesRoot, $"aries-lease-{leaseId}.json");
            await WriteJsonAsync(leasePath, leaseBundle, cancellationToken);
            result.GeneratedFiles.Add(Path.GetFileName(leasePath));
        }

        result.Warnings.Add("Aries bundle export currently produces JSON bundle artifacts. Native Aries .accdb writing is still pending.");
    }

    private static async Task WriteCsvAsync(string csvPath, IReadOnlyList<string> rowJsonValues, CancellationToken cancellationToken)
    {
        var rows = rowJsonValues
            .Select(ParseRow)
            .ToList();

        var columns = rows
            .SelectMany(row => row.Keys)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(column => column, StringComparer.OrdinalIgnoreCase)
            .ToList();

        await using var writer = new StreamWriter(csvPath, false, new UTF8Encoding(false));
        await writer.WriteLineAsync(string.Join(",", columns.Select(EscapeCsv)));

        foreach (var row in rows)
        {
            var orderedValues = columns.Select(column => row.TryGetValue(column, out var value) ? EscapeCsv(value) : string.Empty);
            await writer.WriteLineAsync(string.Join(",", orderedValues));
        }
    }

    private static async Task WriteJsonAsync<T>(string path, T value, CancellationToken cancellationToken)
    {
        await using var stream = File.Create(path);
        await JsonSerializer.SerializeAsync(stream, value, new JsonSerializerOptions { WriteIndented = true }, cancellationToken);
    }

    private async Task GenerateAriesAccessAsync(
        ImportJobRecord job,
        ImportExportRequest request,
        string filesRoot,
        string exportBaseFileName,
        ImportExportResult result,
        CancellationToken cancellationToken)
    {
        if (job.SourceKind != ImportSourceKind.PhdWin)
        {
            throw new InvalidOperationException("Aries Access DB export is currently supported for PHDWin import jobs only.");
        }

        var templatePath = _importTemplateService.GetTemplatePath(ImportTemplateKind.AriesAccess);
        if (!File.Exists(templatePath))
        {
            throw new InvalidOperationException($"The Aries Access template was not found at '{templatePath}'.");
        }

        var extractedDatasource = GetExtractedDatasource(job);
        var extractedPath = Path.Combine(_storageOptions.RootPath, extractedDatasource.Replace('/', Path.DirectorySeparatorChar));
        if (!Directory.Exists(extractedPath))
        {
            throw new InvalidOperationException($"The extracted PHDWin workspace was not found at '{extractedPath}'.");
        }

        var outputFileName = $"{exportBaseFileName}.accdb";
        var outputPath = Path.Combine(filesRoot, outputFileName);
        File.Copy(templatePath, outputPath, true);

        var exportData = await BuildAriesAccessExportDataAsync(job, request, cancellationToken);
        Console.WriteLine(
            "Aries Access export: data loaded " +
            $"property={exportData.MasterRows.Count:N0}, product={exportData.ProductRows.Count:N0}, " +
            $"test={exportData.TestRows.Count:N0}, economic={exportData.EconRows.Count:N0}.");

        var builder = new OdbcConnectionStringBuilder
        {
            ["Driver"] = "{Microsoft Access Driver (*.mdb, *.accdb)}",
            ["Dbq"] = outputPath,
            ["Pooling"] = false
        };

        await using var access = new OdbcConnection(builder.ConnectionString);
        access.Open();

        await WriteLoggedDictionaryTableAsync(access, "AC_PROPERTY", exportData.MasterRows, cancellationToken, preferExistingSchema: true, extendExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AC_PRODUCT", exportData.ProductRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AC_TEST", exportData.TestRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AC_DAILY", exportData.DailyRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AC_ECONOMIC", exportData.EconRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "ARLOOKUP", exportData.LookupRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AR_SIDEFILE", exportData.SidefileRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AC_OWNER", exportData.OwnerRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "GROUPTEST", exportData.GroupListRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AC_SCENARIO", exportData.ScenarioRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "AC_SETUPDATA", exportData.SetupDataRows, cancellationToken, preferExistingSchema: true, appendToExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "PROJECT", exportData.ProjectRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "PROJLIST", exportData.ProjlistRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "SORTFILTERS", exportData.SortFilterRows, cancellationToken, preferExistingSchema: true);
        await WriteLoggedObjectTableAsync(access, "SelFilters", exportData.SelFilterRows, cancellationToken, preferExistingSchema: true);

        result.GeneratedFiles.Add(outputFileName);
        result.Warnings.Add("Aries Access DB export now prefers the resolved Aries PostgreSQL dataset as its source contract and recreates AC_PROPERTY from that resolved shape. Additional downstream Aries tables are still pending.");
    }

    private async Task<AriesAccessExportData> BuildAriesAccessExportDataAsync(
        ImportJobRecord job,
        ImportExportRequest request,
        CancellationToken cancellationToken)
    {
        if (!string.IsNullOrWhiteSpace(job.AriesResolvedSchema) && !string.IsNullOrWhiteSpace(_postgresOptions.ConnectionString))
        {
            Console.WriteLine($"Aries Access export: loading resolved Aries data from PostgreSQL schema {job.AriesResolvedSchema}.");
            return await BuildAriesAccessExportDataFromResolvedAsync(job, request, cancellationToken);
        }

        Console.WriteLine("Aries Access export: loading Aries data from PHDWin datasource fallback.");
        using var scope = _serviceProvider.CreateScope();
        var importScopedAriesService = scope.ServiceProvider.GetRequiredService<IImportScopedAriesService>();
        var availableLeaseIds = await importScopedAriesService.GetExportLeaseIdsAsync(job.JobId, cancellationToken);
        var requestedLeaseIds = request.LeaseIds
            .Distinct()
            .OrderBy(x => x)
            .ToList();
        var leaseIds = requestedLeaseIds.Count == 0
            ? availableLeaseIds
            : availableLeaseIds.Where(leaseId => requestedLeaseIds.Contains(leaseId)).ToList();

        if (requestedLeaseIds.Count > 0 && leaseIds.Count == 0)
        {
            throw new InvalidOperationException("Aries Access DB export did not match any requested lease ids.");
        }

        return await ExecuteAgainstJobDatasourceAsync(job, async scopedProvider =>
        {
            var ariesExportService = scopedProvider.GetRequiredService<IAriesExportService>();
            var masterRows = new List<Dictionary<string, object>>();
            var productRows = new List<ProductEntity>();
            var testRows = new List<TestEntity>();
            var dailyRows = new List<DailyExportEntity>();
            var econRows = new List<AriesEconEntity>();

            foreach (var leaseId in leaseIds)
            {
                cancellationToken.ThrowIfCancellationRequested();
                masterRows.AddRange(await importScopedAriesService.GetMasterTableAsync(job.JobId, leaseId, cancellationToken));
                productRows.AddRange(await ariesExportService.GetProductTableAsync(leaseId));
                testRows.AddRange(await ariesExportService.GetTestTableAsync(leaseId));
                dailyRows.AddRange(await importScopedAriesService.GetDailyTableAsync(job.JobId, leaseId, cancellationToken));
                econRows.AddRange(await ariesExportService.GetLeaseEconTableAsync(leaseId));
            }

            return new AriesAccessExportData
            {
                MasterRows = masterRows,
                ProductRows = productRows,
                TestRows = testRows,
                DailyRows = dailyRows,
                EconRows = econRows.OrderBy(row => row.Propnum).ThenBy(row => row.Section).ThenBy(row => row.Sequence).ToList(),
                LookupRows = await importScopedAriesService.GetLookupTableAsync(job.JobId, cancellationToken),
                SidefileRows = await ariesExportService.GetSidefileEntitiesAsync(),
                OwnerRows = await importScopedAriesService.GetGroupsTableAsync(job.JobId, cancellationToken),
                GroupListRows = await importScopedAriesService.GetGroupListTableAsync(job.JobId, cancellationToken),
                ScenarioRows = await importScopedAriesService.GetScenarioTableAsync(job.JobId, cancellationToken),
                SetupDataRows = await importScopedAriesService.GetSetupDataTableAsync(job.JobId, cancellationToken),
                ProjectRows = await importScopedAriesService.GetProjectTableAsync(job.JobId, leaseIds, cancellationToken),
                ProjlistRows = await importScopedAriesService.GetProjlistTableAsync(job.JobId, leaseIds, cancellationToken),
                SortFilterRows = await importScopedAriesService.GetSortFiltersTableAsync(job.JobId, leaseIds, cancellationToken),
                SelFilterRows = await importScopedAriesService.GetSelFiltersTableAsync(job.JobId, leaseIds, cancellationToken)
            };
        });
    }

    private async Task<AriesAccessExportData> BuildAriesAccessExportDataFromResolvedAsync(
        ImportJobRecord job,
        ImportExportRequest request,
        CancellationToken cancellationToken)
    {
        await using var connection = new NpgsqlConnection(_postgresOptions.ConnectionString);
        await connection.OpenAsync(cancellationToken);

        var importScopedAriesService = _serviceProvider.GetRequiredService<IImportScopedAriesService>();
        var availableLeaseIds = await importScopedAriesService.GetExportLeaseIdsAsync(job.JobId, cancellationToken);
        var requestedLeaseIds = request.LeaseIds
            .Distinct()
            .OrderBy(x => x)
            .ToList();
        var leaseIds = requestedLeaseIds.Count == 0
            ? availableLeaseIds
            : availableLeaseIds.Where(leaseId => requestedLeaseIds.Contains(leaseId)).ToList();

        if (requestedLeaseIds.Count > 0 && leaseIds.Count == 0)
        {
            throw new InvalidOperationException("Aries Access DB export did not match any requested lease ids.");
        }

        var schemaName = job.AriesResolvedSchema!;
        Console.WriteLine("Aries Access export: loading lease ids.");
        Console.WriteLine($"Aries Access export: selected {leaseIds.Count:N0} lease ids.");

        Console.WriteLine("Aries Access export: loading AC_PROPERTY source rows.");
        var masterRows = await LoadResolvedDictionaryRowsAsync(connection, schemaName, "aries_property", leaseIds, cancellationToken);
        Console.WriteLine($"Aries Access export: loaded AC_PROPERTY source rows ({masterRows.Count:N0}).");

        Console.WriteLine("Aries Access export: loading AC_PRODUCT source rows.");
        var productRows = await LoadResolvedTypedRowsAsync<ProductEntity>(connection, schemaName, "aries_product", leaseIds, cancellationToken);
        Console.WriteLine($"Aries Access export: loaded AC_PRODUCT source rows ({productRows.Count:N0}).");

        Console.WriteLine("Aries Access export: loading AC_TEST source rows.");
        var testRows = await LoadResolvedTypedRowsAsync<TestEntity>(connection, schemaName, "aries_test", leaseIds, cancellationToken);
        Console.WriteLine($"Aries Access export: loaded AC_TEST source rows ({testRows.Count:N0}).");

        Console.WriteLine("Aries Access export: loading AC_ECONOMIC source rows.");
        var econRows = await LoadResolvedTypedRowsAsync<AriesEconEntity>(connection, schemaName, "aries_economic", leaseIds, cancellationToken);
        Console.WriteLine($"Aries Access export: loaded AC_ECONOMIC source rows ({econRows.Count:N0}).");

        Console.WriteLine("Aries Access export: loading reference rows.");
        var lookupRows = await LoadResolvedReferenceRowsAsync<LookupRow>(connection, schemaName, "aries_lookup", cancellationToken);
        var sidefileRows = await LoadResolvedReferenceRowsAsync<AriesSidefileEntity>(connection, schemaName, "aries_sidefile", cancellationToken);
        var ownerRows = await LoadResolvedReferenceRowsAsync<AriesGroupsEntity>(connection, schemaName, "aries_owner", cancellationToken);
        var groupListRows = await LoadResolvedReferenceRowsAsync<GroupListEntity>(connection, schemaName, "aries_group_list", cancellationToken);
        var scenarioRows = await LoadResolvedReferenceRowsAsync<ScenarioRow>(connection, schemaName, "aries_scenario", cancellationToken);
        var setupDataRows = await LoadResolvedReferenceRowsAsync<SetupDataEntity>(connection, schemaName, "aries_setup_data", cancellationToken);
        var projectRows = await LoadResolvedReferenceRowsAsync<ProjectEntity>(connection, schemaName, "aries_project", cancellationToken);
        var projlistRows = await LoadResolvedReferenceRowsAsync<ProjlistEntity>(connection, schemaName, "aries_projlist", cancellationToken);
        var sortFilterRows = await LoadResolvedReferenceRowsAsync<SortFilterEntity>(connection, schemaName, "aries_sortfilters", cancellationToken);
        var selFilterRows = await importScopedAriesService.GetSelFiltersTableAsync(job.JobId, leaseIds, cancellationToken);
        Console.WriteLine("Aries Access export: loaded reference rows.");

        return new AriesAccessExportData
        {
            MasterRows = masterRows,
            ProductRows = productRows,
            TestRows = testRows,
            DailyRows = new List<DailyExportEntity>(),
            EconRows = econRows,
            LookupRows = lookupRows,
            SidefileRows = sidefileRows,
            OwnerRows = ownerRows,
            GroupListRows = groupListRows,
            ScenarioRows = scenarioRows,
            SetupDataRows = setupDataRows,
            ProjectRows = projectRows,
            ProjlistRows = projlistRows,
            SortFilterRows = sortFilterRows,
            SelFilterRows = selFilterRows
        };
    }

    private static async Task<List<Dictionary<string, object>>> BuildCurrentMasterRowsAsync(
        IImportScopedAriesService importScopedAriesService,
        Guid jobId,
        IReadOnlyList<short> leaseIds,
        CancellationToken cancellationToken)
    {
        var rows = await importScopedAriesService.GetMasterTableAsync(jobId, null, cancellationToken);
        var selectedLeaseIds = leaseIds.ToHashSet();
        return rows
            .Where(row => row.TryGetValue("lse_id", out var leaseIdValue)
                && short.TryParse(leaseIdValue?.ToString(), out var leaseId)
                && selectedLeaseIds.Contains(leaseId))
            .ToList();
    }

    private async Task<T> ExecuteAgainstJobDatasourceAsync<T>(
        ImportJobRecord job,
        Func<IServiceProvider, Task<T>> action)
    {
        var httpContext = _httpContextAccessor.HttpContext
                          ?? throw new InvalidOperationException("Aries Access export requires an active HTTP context.");

        var datasource = GetExtractedDatasource(job);
        var previousDatasource = httpContext.Request.Headers.TryGetValue("datasource", out var existingDatasource)
            ? existingDatasource.ToString()
            : null;
        var previousMimetype = httpContext.Request.Headers.TryGetValue("mimetype", out var existingMimetype)
            ? existingMimetype.ToString()
            : null;
        var previousLockedDatasource = httpContext.Items.TryGetValue("LockedDatasource", out var existingLockedDatasource)
            ? existingLockedDatasource
            : null;

        httpContext.Request.Headers["datasource"] = datasource;
        httpContext.Request.Headers["mimetype"] = "application/vnd.phdwin2";
        httpContext.Items["LockedDatasource"] = datasource;

        try
        {
            using var scope = _serviceProvider.CreateScope();
            return await action(scope.ServiceProvider);
        }
        finally
        {
            if (previousDatasource is null)
            {
                httpContext.Request.Headers.Remove("datasource");
            }
            else
            {
                httpContext.Request.Headers["datasource"] = previousDatasource;
            }

            if (previousMimetype is null)
            {
                httpContext.Request.Headers.Remove("mimetype");
            }
            else
            {
                httpContext.Request.Headers["mimetype"] = previousMimetype;
            }

            if (previousLockedDatasource is null)
            {
                httpContext.Items.Remove("LockedDatasource");
            }
            else
            {
                httpContext.Items["LockedDatasource"] = previousLockedDatasource;
            }
        }
    }

    private static string GetExtractedDatasource(ImportJobRecord job)
    {
        return $"{job.WorkspaceRelativePath.TrimEnd('/')}/extracted";
    }

    private async Task GeneratePhdWinAccessAsync(
        ImportJobRecord job,
        string filesRoot,
        IReadOnlyCollection<string>? requestedTables,
        string exportBaseFileName,
        ImportExportResult result,
        CancellationToken cancellationToken)
    {
        if (job.SourceKind != ImportSourceKind.PhdWin)
        {
            throw new InvalidOperationException("PHDWin Access DB export is currently supported for PHDWin import jobs only.");
        }

        var templatePath = _importTemplateService.GetTemplatePath(ImportTemplateKind.PhdWinAccess);
        if (!File.Exists(templatePath))
        {
            throw new InvalidOperationException($"The PHDWin Access template was not found at '{templatePath}'.");
        }

        var outputFileName = $"{exportBaseFileName}.accdb";
        var outputPath = Path.Combine(filesRoot, outputFileName);
        File.Copy(templatePath, outputPath, true);

        var exportTables = await LoadAccessExportTablesAsync(job, requestedTables, cancellationToken);
        var builder = new OdbcConnectionStringBuilder
        {
            ["Driver"] = "{Microsoft Access Driver (*.mdb, *.accdb)}",
            ["Dbq"] = outputPath,
            ["Pooling"] = false
        };

        await using var connection = new OdbcConnection(builder.ConnectionString);
        connection.Open();

        foreach (var table in exportTables)
        {
            cancellationToken.ThrowIfCancellationRequested();
            await DropTableIfExistsAsync(connection, table.AccessTableName, cancellationToken);
            await CreateAccessTableAsync(connection, table, cancellationToken);
            await InsertAccessRowsFromWorkspaceAsync(connection, job.JobId, table, cancellationToken);
        }

        result.GeneratedFiles.Add(outputFileName);
    }

    private static async Task<List<Dictionary<string, string>>> LoadResolvedRowsAsync(
        NpgsqlConnection connection,
        string schemaName,
        string tableName,
        CancellationToken cancellationToken)
    {
        var rows = await connection.QueryAsync<string>(
            $"""
            select row_data::text
            from {QuoteIdentifier(schemaName)}.{QuoteIdentifier(tableName)}
            order by lease_id, row_ordinal;
            """);
        cancellationToken.ThrowIfCancellationRequested();
        return rows.Select(ParseRow).ToList();
    }

    private static async Task<List<Dictionary<string, object>>> LoadResolvedDictionaryRowsAsync(
        NpgsqlConnection connection,
        string schemaName,
        string tableName,
        IReadOnlyList<short> leaseIds,
        CancellationToken cancellationToken)
    {
        var rows = await LoadResolvedLeaseScopedRowJsonAsync(connection, schemaName, tableName, leaseIds, cancellationToken);
        return rows
            .Select(ParseRow)
            .Select(row => row.ToDictionary(pair => pair.Key, pair => (object)pair.Value, StringComparer.OrdinalIgnoreCase))
            .ToList();
    }

    private static async Task<List<T>> LoadResolvedTypedRowsAsync<T>(
        NpgsqlConnection connection,
        string schemaName,
        string tableName,
        IReadOnlyList<short> leaseIds,
        CancellationToken cancellationToken)
    {
        var rows = await LoadResolvedLeaseScopedRowJsonAsync(connection, schemaName, tableName, leaseIds, cancellationToken);
        return DeserializeResolvedRows<T>(rows);
    }

    private static async Task<List<T>> LoadResolvedReferenceRowsAsync<T>(
        NpgsqlConnection connection,
        string schemaName,
        string tableName,
        CancellationToken cancellationToken)
    {
        var rows = await connection.QueryAsync<string>(
            $"""
            select row_data::text
            from {QuoteIdentifier(schemaName)}.{QuoteIdentifier(tableName)}
            order by row_ordinal;
            """);

        cancellationToken.ThrowIfCancellationRequested();
        return DeserializeResolvedRows<T>(rows);
    }

    private static async Task<List<string>> LoadResolvedLeaseScopedRowJsonAsync(
        NpgsqlConnection connection,
        string schemaName,
        string tableName,
        IReadOnlyList<short> leaseIds,
        CancellationToken cancellationToken)
    {
        if (leaseIds.Count == 0)
        {
            return new List<string>();
        }

        var rows = await connection.QueryAsync<string>(
            $"""
            select row_data::text
            from {QuoteIdentifier(schemaName)}.{QuoteIdentifier(tableName)}
            where lease_id = any(@LeaseIds)
            order by lease_id, row_ordinal;
            """,
            new { LeaseIds = leaseIds.ToArray() });

        cancellationToken.ThrowIfCancellationRequested();
        return rows.ToList();
    }

    private static List<T> DeserializeResolvedRows<T>(IEnumerable<string> rows)
    {
        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };

        var results = new List<T>();
        foreach (var row in rows)
        {
            var deserialized = JsonSerializer.Deserialize<T>(row, options);
            if (deserialized is not null)
            {
                results.Add(deserialized);
            }
        }

        return results;
    }

    private static Dictionary<string, string> ParseRow(string json)
    {
        using var document = JsonDocument.Parse(json);
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var property in document.RootElement.EnumerateObject())
        {
            result[property.Name] = ConvertJsonValue(property.Value);
        }

        return result;
    }

    private static string ConvertJsonValue(JsonElement value)
    {
        return value.ValueKind switch
        {
            JsonValueKind.Null => string.Empty,
            JsonValueKind.String => value.GetString() ?? string.Empty,
            JsonValueKind.Number => value.ToString(),
            JsonValueKind.True => bool.TrueString,
            JsonValueKind.False => bool.FalseString,
            _ => value.ToString()
        };
    }

    private static string EscapeCsv(string? value)
    {
        if (string.IsNullOrEmpty(value))
        {
            return string.Empty;
        }

        if (value.Contains('"') || value.Contains(',') || value.Contains('\n') || value.Contains('\r'))
        {
            return $"\"{value.Replace("\"", "\"\"")}\"";
        }

        return value;
    }

    private static string SanitizeFileName(string fileName)
    {
        var invalidChars = Path.GetInvalidFileNameChars();
        var buffer = new StringBuilder(fileName.Length);
        foreach (var character in fileName)
        {
            buffer.Append(invalidChars.Contains(character) ? '_' : character);
        }

        return buffer.ToString();
    }

    private static string BuildExportBaseFileName(ImportJobRecord job, DateTime createdAtUtc)
    {
        var sourceFileName = job.ExtractedFiles
            .Concat(job.UploadedFiles)
            .FirstOrDefault(file => string.Equals(file.Extension, ".phd", StringComparison.OrdinalIgnoreCase))
            ?.OriginalName;

        if (string.IsNullOrWhiteSpace(sourceFileName))
        {
            sourceFileName = job.UploadedFiles
                .Concat(job.ExtractedFiles)
                .FirstOrDefault(file => !string.IsNullOrWhiteSpace(file.OriginalName))
                ?.OriginalName;
        }

        var baseName = string.IsNullOrWhiteSpace(sourceFileName)
            ? $"import-{job.JobId:N}"
            : Path.GetFileNameWithoutExtension(sourceFileName);
        var timestamp = createdAtUtc.ToString("yyyyMMdd-HHmmss", System.Globalization.CultureInfo.InvariantCulture);

        return SanitizeFileName($"{baseName}-{timestamp}");
    }

    private async Task GenerateExposureCsvAsync(
        ImportJobRecord job,
        string exportPresetKey,
        string filesRoot,
        ImportExportResult result,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(_postgresOptions.ConnectionString))
        {
            throw new InvalidOperationException("Preset exports require PostgreSQL-backed exposure views.");
        }

        var dataset = job.ExposureDatasets.FirstOrDefault(d => string.Equals(d.DatasetKey, exportPresetKey, StringComparison.OrdinalIgnoreCase));
        if (dataset == null || string.IsNullOrWhiteSpace(dataset.ExportViewName))
        {
            throw new InvalidOperationException($"Export preset '{exportPresetKey}' is not available for this import job.");
        }

        try
        {
            await using var connection = new NpgsqlConnection(_postgresOptions.ConnectionString);
            await connection.OpenAsync(cancellationToken);

            var schemaName = job.PostgresSchema ?? GetSchemaName(job.JobId);
            var rows = (await connection.QueryAsync(
                $"""
                select *
                from {QuoteIdentifier(schemaName)}.{QuoteIdentifier(dataset.ExportViewName)}
                """)).Cast<IDictionary<string, object?>>().ToList();

            var csvPath = Path.Combine(filesRoot, $"{SanitizeFileName(dataset.Title)}.csv");
            await WriteCsvAsync(csvPath, rows.Select(SerializeDynamicRow).ToList(), cancellationToken);
            result.GeneratedFiles.Add(Path.GetFileName(csvPath));
        }
        catch (NpgsqlException ex)
        {
            throw new InvalidOperationException(
                $"Export preset '{exportPresetKey}' requires a working PostgreSQL connection. PostgreSQL is unavailable ({ex.SqlState ?? "n/a"}): {ex.Message}",
                ex);
        }
    }

    private static string SerializeDynamicRow(IDictionary<string, object?> row)
    {
        var normalized = row.ToDictionary(
            pair => pair.Key,
            pair => pair.Value,
            StringComparer.OrdinalIgnoreCase);
        return JsonSerializer.Serialize(normalized);
    }

    private async Task<WorkspaceStagingManifest> LoadWorkspaceManifestAsync(Guid jobId, CancellationToken cancellationToken)
    {
        var manifestPath = _importJobService.GetWorkspacePath(jobId, "staged", "manifest.json");
        if (!File.Exists(manifestPath))
        {
            throw new InvalidOperationException("No staged workspace data was found for this job.");
        }

        await using var stream = File.OpenRead(manifestPath);
        return await JsonSerializer.DeserializeAsync<WorkspaceStagingManifest>(stream, cancellationToken: cancellationToken)
               ?? throw new InvalidOperationException("The staged workspace manifest could not be read.");
    }

    private async Task<List<Dictionary<string, object?>>> LoadWorkspaceRowsAsync(Guid jobId, string fileName, CancellationToken cancellationToken)
    {
        var filePath = _importJobService.GetWorkspacePath(jobId, "staged", fileName);
        await using var stream = File.OpenRead(filePath);
        return await JsonSerializer.DeserializeAsync<List<Dictionary<string, object?>>>(stream, cancellationToken: cancellationToken)
               ?? new List<Dictionary<string, object?>>();
    }

    private async IAsyncEnumerable<Dictionary<string, string>> StreamWorkspaceRowsAsync(
        Guid jobId,
        string fileName,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var filePath = _importJobService.GetWorkspacePath(jobId, "staged", fileName);
        await using var stream = File.OpenRead(filePath);
        await foreach (var row in JsonSerializer.DeserializeAsyncEnumerable<Dictionary<string, JsonElement>>(stream, cancellationToken: cancellationToken))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (row == null)
            {
                continue;
            }

            yield return row.ToDictionary(
                pair => pair.Key,
                pair => ConvertJsonValue(pair.Value),
                StringComparer.OrdinalIgnoreCase);
        }
    }

    private static async Task<List<WorkspaceStagedTable>> LoadPostgresManifestAsync(NpgsqlConnection connection, Guid jobId, CancellationToken cancellationToken)
    {
        var schemaName = GetSchemaName(jobId);
        var rows = await connection.QueryAsync<WorkspaceStagedTable>(
            $"""
            select
                source_table as {nameof(WorkspaceStagedTable.SourceTable)},
                logical_table as {nameof(WorkspaceStagedTable.LogicalTableName)},
                source_kind as {nameof(WorkspaceStagedTable.SourceKind)},
                postgres_table as {nameof(WorkspaceStagedTable.PostgresTableName)},
                row_count as {nameof(WorkspaceStagedTable.RowCount)},
                column_count as {nameof(WorkspaceStagedTable.ColumnCount)}
            from {QuoteIdentifier(schemaName)}.{QuoteIdentifier("__table_manifest")}
            order by
                case source_kind
                    when 'PHD' then 0
                    when 'MOD' then 1
                    else 2
                end,
                logical_table;
            """);
        cancellationToken.ThrowIfCancellationRequested();
        return rows.ToList();
    }

    private static string GetSchemaName(Guid jobId)
    {
        return $"job_{jobId:N}";
    }

    private static string QuoteIdentifier(string identifier)
    {
        return "\"" + identifier.Replace("\"", "\"\"") + "\"";
    }

    private async Task<List<AccessExportTable>> LoadAccessExportTablesAsync(
        ImportJobRecord job,
        IReadOnlyCollection<string>? requestedTables,
        CancellationToken cancellationToken)
    {
        var workspaceManifest = await LoadWorkspaceManifestAsync(job.JobId, cancellationToken);
        var selectedTables = FilterTables(workspaceManifest.Tables, requestedTables);
        var accessTables = new List<AccessExportTable>(selectedTables.Count);

        foreach (var table in selectedTables)
        {
            var selectedColumns = await ResolveWorkspaceColumnsAsync(job.JobId, table, cancellationToken);
            var columnMap = BuildAccessIdentifierMap(selectedColumns, 64);
            var accessTableName = BuildAccessIdentifierMap(new[] { table.LogicalTableName }, 64)[table.LogicalTableName];

            accessTables.Add(new AccessExportTable
            {
                FileName = table.FileName,
                LogicalTableName = table.LogicalTableName,
                AccessTableName = accessTableName,
                OriginalColumns = selectedColumns,
                AccessColumns = selectedColumns.Select(column => columnMap[column]).ToList()
            });
        }

        return accessTables;
    }

    private async Task<List<string>> ResolveWorkspaceColumnsAsync(Guid jobId, WorkspaceStagedTable table, CancellationToken cancellationToken)
    {
        if (table.ColumnNames.Count > 0)
        {
            return table.ColumnNames.Take(AccessExportColumnCount).ToList();
        }

        await foreach (var row in StreamWorkspaceRowsAsync(jobId, table.FileName, cancellationToken))
        {
            return row.Keys.Take(AccessExportColumnCount).ToList();
        }

        return new List<string>();
    }

    private async Task<List<WorkspaceStagedTable>> LoadSelectedTableMetadataAsync(
        ImportJobRecord job,
        IReadOnlyCollection<string>? requestedTables,
        ImportExportResult result,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(_postgresOptions.ConnectionString))
        {
            var workspaceManifest = await LoadWorkspaceManifestAsync(job.JobId, cancellationToken);
            return FilterTables(workspaceManifest.Tables, requestedTables);
        }

        try
        {
            await using var connection = new NpgsqlConnection(_postgresOptions.ConnectionString);
            await connection.OpenAsync(cancellationToken);
            var postgresManifest = await LoadPostgresManifestAsync(connection, job.JobId, cancellationToken);
            return FilterTables(postgresManifest, requestedTables);
        }
        catch (NpgsqlException ex)
        {
            result.Warnings.Add($"PostgreSQL export staging is unavailable ({ex.SqlState ?? "n/a"}). Falling back to staged workspace files for table metadata and raw-table export.");
            var workspaceManifest = await LoadWorkspaceManifestAsync(job.JobId, cancellationToken);
            return FilterTables(workspaceManifest.Tables, requestedTables);
        }
    }

    private static List<WorkspaceStagedTable> FilterTables(IEnumerable<WorkspaceStagedTable> tables, IReadOnlyCollection<string>? requestedTables)
    {
        return (requestedTables == null
                ? tables
                : tables.Where(t => requestedTables.Contains(t.LogicalTableName, StringComparer.OrdinalIgnoreCase)))
            .OrderBy(t => ImportTableNameHelper.GetSourceSortRank(t.SourceKind))
            .ThenBy(t => t.LogicalTableName, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static AccessExportPlan? BuildAccessExportPlan(
        ISet<string> normalizedFormats,
        IReadOnlyList<WorkspaceStagedTable> selectedTables)
    {
        var accessRequested = normalizedFormats.Contains("phdwin_access") || normalizedFormats.Contains("aries_accdb");
        if (!accessRequested)
        {
            return null;
        }

        var estimatedBytes = selectedTables.Sum(table => EstimateTableBytes(table.RowCount, table.ColumnCount));
        return new AccessExportPlan
        {
            Requested = true,
            ColumnLimit = AccessExportColumnCount,
            EstimatedTotalBytes = estimatedBytes,
            EstimatedSizeExceedsLimit = estimatedBytes >= AccessRecommendedMaxBytes,
            Tables = selectedTables
                .Select(table => new AccessTablePlan
                {
                    LogicalTableName = table.LogicalTableName,
                    RowCount = table.RowCount,
                    SourceColumnCount = table.ColumnCount,
                    AccessColumnCount = Math.Min(table.ColumnCount, AccessExportColumnCount),
                    DroppedColumnCount = Math.Max(0, table.ColumnCount - AccessExportColumnCount),
                    WillTruncateColumns = table.ColumnCount > AccessExportColumnCount
                })
                .ToList()
        };
    }

    private static void AddAccessWarnings(AccessExportPlan? accessExportPlan, ImportExportResult result)
    {
        if (accessExportPlan is null || !accessExportPlan.Requested)
        {
            return;
        }

        var truncatedTables = accessExportPlan.Tables
            .Where(table => table.WillTruncateColumns)
            .OrderByDescending(table => table.SourceColumnCount)
            .Select(table => $"{table.LogicalTableName} ({table.SourceColumnCount} columns, drop {table.DroppedColumnCount})")
            .ToList();

        if (truncatedTables.Count > 0)
        {
            result.Warnings.Add($"Access export shape: {truncatedTables.Count} selected table(s) exceed {accessExportPlan.ColumnLimit} columns and will be truncated to the first {accessExportPlan.ColumnLimit} columns in Access output: {string.Join(", ", truncatedTables)}.");
        }

        if (accessExportPlan.EstimatedSizeExceedsLimit)
        {
            var estimatedGb = accessExportPlan.EstimatedTotalBytes / (1024d * 1024d * 1024d);
            result.Warnings.Add($"Access export limit: estimated selected dataset size is about {estimatedGb:F2} GB, which meets or exceeds the practical 2 GB Access file-size limit.");
        }
    }

    private static long EstimateTableBytes(int rowCount, int columnCount)
    {
        const int estimatedBytesPerCell = 32;
        const int estimatedBytesPerRowOverhead = 128;
        return ((long)rowCount * columnCount * estimatedBytesPerCell) + ((long)rowCount * estimatedBytesPerRowOverhead);
    }

    private static Dictionary<string, string> BuildAccessIdentifierMap(IEnumerable<string> sourceNames, int maxLength)
    {
        var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var usedNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var sourceName in sourceNames)
        {
            map[sourceName] = BuildAccessIdentifier(sourceName, maxLength, usedNames);
        }

        return map;
    }

    private static string BuildAccessIdentifier(string sourceName, int maxLength, ISet<string> usedNames)
    {
        var normalized = new string(sourceName
            .Select(character => char.IsLetterOrDigit(character) || character == '_' ? character : '_')
            .ToArray())
            .Trim('_');

        if (string.IsNullOrWhiteSpace(normalized))
        {
            normalized = "Field";
        }

        if (char.IsDigit(normalized[0]))
        {
            normalized = "_" + normalized;
        }

        if (normalized.Length > maxLength)
        {
            normalized = normalized[..maxLength];
        }

        normalized = normalized.ToUpperInvariant();

        var candidate = normalized;
        var suffix = 1;
        while (!usedNames.Add(candidate))
        {
            var suffixText = $"_{suffix++}";
            var prefixLength = Math.Max(1, maxLength - suffixText.Length);
            candidate = normalized[..Math.Min(prefixLength, normalized.Length)] + suffixText;
        }

        return candidate;
    }

    private static async Task DropTableIfExistsAsync(OdbcConnection connection, string tableName, CancellationToken cancellationToken)
    {
        try
        {
            await using var command = new OdbcCommand($"DROP TABLE {QuoteAccessIdentifier(tableName)}", connection);
            await command.ExecuteNonQueryAsync(cancellationToken);
        }
        catch
        {
        }
    }

    private static async Task RecreateAccessTableAsync(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<string> columns,
        CancellationToken cancellationToken)
    {
        await DropTableIfExistsAsync(connection, tableName, cancellationToken);
        var columnsSql = string.Join(", ", columns.Select(column => $"{QuoteAccessIdentifier(column)} LONGTEXT"));
        await using var command = new OdbcCommand($"CREATE TABLE {QuoteAccessIdentifier(tableName)} ({columnsSql})", connection);
        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private static async Task<IReadOnlyList<AccessColumnSchema>> ExtendExistingAccessSchemaAsync(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<AccessColumnSchema> existingColumnSchemas,
        IReadOnlyList<string> sourceColumns,
        CancellationToken cancellationToken)
    {
        var expandedColumnSchemas = existingColumnSchemas.ToList();
        var existingNormalizedNames = existingColumnSchemas
            .Select(column => NormalizeAccessColumnName(column.Name))
            .ToHashSet(StringComparer.OrdinalIgnoreCase);
        var usedNames = existingColumnSchemas
            .Select(column => column.Name)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        foreach (var sourceColumn in sourceColumns)
        {
            var accessColumnName = BuildAccessIdentifier(sourceColumn, 64, usedNames);
            var normalizedAccessColumnName = NormalizeAccessColumnName(accessColumnName);
            if (!existingNormalizedNames.Add(normalizedAccessColumnName))
            {
                continue;
            }

            await using var command = new OdbcCommand(
                $"ALTER TABLE {QuoteAccessIdentifier(tableName)} ADD COLUMN {QuoteAccessIdentifier(accessColumnName)} LONGTEXT",
                connection);
            await command.ExecuteNonQueryAsync(cancellationToken);

            expandedColumnSchemas.Add(new AccessColumnSchema
            {
                Name = accessColumnName,
                DataType = typeof(string)
            });
        }

        return expandedColumnSchemas;
    }

    private static Task DeleteAllRowsAsync(
        OdbcConnection connection,
        string tableName,
        CancellationToken cancellationToken)
    {
        return ExecuteNonQueryAsync(connection, $"DELETE FROM {QuoteAccessIdentifier(tableName)}", cancellationToken);
    }

    private static async Task<IReadOnlyList<string>> GetExistingAccessColumnsAsync(
        OdbcConnection connection,
        string tableName,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();

        var schema = connection.GetSchema("Columns", new[] { null, null, tableName, null });
        if (schema.Rows.Count == 0)
        {
            return Array.Empty<string>();
        }

        var ordered = schema.Rows
            .Cast<System.Data.DataRow>()
            .OrderBy(row => row.Table.Columns.Contains("ORDINAL_POSITION") ? Convert.ToInt32(row["ORDINAL_POSITION"]) : int.MaxValue)
            .Select(row => row["COLUMN_NAME"]?.ToString())
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Cast<string>()
            .ToList();

        return ordered;
    }

    private static async Task<IReadOnlyList<AccessColumnSchema>> GetExistingAccessColumnSchemasAsync(
        OdbcConnection connection,
        string tableName,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();

        await using var command = new OdbcCommand($"SELECT * FROM {QuoteAccessIdentifier(tableName)} WHERE 1 = 0", connection);
        await using var reader = await command.ExecuteReaderAsync(System.Data.CommandBehavior.SchemaOnly, cancellationToken);
        var schemaTable = reader.GetSchemaTable();
        var schema = new List<AccessColumnSchema>();

        for (var index = 0; index < reader.FieldCount; index++)
        {
            var columnSize = 0;
            if (schemaTable != null && index < schemaTable.Rows.Count && schemaTable.Columns.Contains("ColumnSize"))
            {
                var value = schemaTable.Rows[index]["ColumnSize"];
                if (value != DBNull.Value)
                {
                    columnSize = Convert.ToInt32(value);
                }
            }

            schema.Add(new AccessColumnSchema
            {
                Name = reader.GetName(index),
                DataType = reader.GetFieldType(index),
                ColumnSize = columnSize
            });
        }

        return schema;
    }

    private static async Task ExecuteNonQueryAsync(
        OdbcConnection connection,
        string sql,
        CancellationToken cancellationToken)
    {
        await using var command = new OdbcCommand(sql, connection);
        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private static async Task CreateAccessTableAsync(OdbcConnection connection, AccessExportTable table, CancellationToken cancellationToken)
    {
        if (table.AccessColumns.Count == 0)
        {
            return;
        }

        var columnsSql = string.Join(", ", table.AccessColumns.Select(column => $"{QuoteAccessIdentifier(column)} LONGTEXT"));
        var createSql = $"CREATE TABLE {QuoteAccessIdentifier(table.AccessTableName)} ({columnsSql})";
        await using var command = new OdbcCommand(createSql, connection);
        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private async Task InsertAccessRowsFromWorkspaceAsync(OdbcConnection connection, Guid jobId, AccessExportTable table, CancellationToken cancellationToken)
    {
        if (table.AccessColumns.Count == 0)
        {
            return;
        }

        var columnSql = string.Join(", ", table.AccessColumns.Select(QuoteAccessIdentifier));
        var parameterSql = string.Join(", ", Enumerable.Repeat("?", table.AccessColumns.Count));
        var insertSql = $"INSERT INTO {QuoteAccessIdentifier(table.AccessTableName)} ({columnSql}) VALUES ({parameterSql})";
        var columnMap = table.OriginalColumns
            .Select((column, index) => new { Source = column, Access = table.AccessColumns[index] })
            .ToDictionary(pair => pair.Source, pair => pair.Access, StringComparer.OrdinalIgnoreCase);
        var batch = new List<Dictionary<string, string>>(AccessInsertBatchSize);

        await foreach (var row in StreamWorkspaceRowsAsync(jobId, table.FileName, cancellationToken))
        {
            var projectedRow = table.OriginalColumns.ToDictionary(
                column => columnMap[column],
                column => row.TryGetValue(column, out var value) ? value : string.Empty,
                StringComparer.OrdinalIgnoreCase);
            batch.Add(projectedRow);

            if (batch.Count >= AccessInsertBatchSize)
            {
                await InsertAccessBatchAsync(connection, insertSql, table.AccessColumns, batch, cancellationToken);
                batch.Clear();
            }
        }

        if (batch.Count > 0)
        {
            await InsertAccessBatchAsync(connection, insertSql, table.AccessColumns, batch, cancellationToken);
            batch.Clear();
        }
    }

    private static async Task InsertAccessBatchAsync(
        OdbcConnection connection,
        string insertSql,
        IReadOnlyList<string> accessColumns,
        IReadOnlyList<Dictionary<string, string>> batch,
        CancellationToken cancellationToken)
    {
        await using var command = new OdbcCommand(insertSql, connection);
        foreach (var _ in accessColumns)
        {
            command.Parameters.Add(string.Empty, OdbcType.NVarChar);
        }

        foreach (var row in batch)
        {
            cancellationToken.ThrowIfCancellationRequested();
            for (var columnIndex = 0; columnIndex < accessColumns.Count; columnIndex++)
            {
                var column = accessColumns[columnIndex];
                command.Parameters[columnIndex].Value = row.TryGetValue(column, out var value) ? value : string.Empty;
            }

            await command.ExecuteNonQueryAsync(cancellationToken);
        }
    }

    private static async Task InsertResolvedRowsAsync(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<string> columns,
        IReadOnlyList<Dictionary<string, string>> rows,
        CancellationToken cancellationToken)
    {
        if (rows.Count == 0)
        {
            return;
        }

        var columnSql = string.Join(", ", columns.Select(QuoteAccessIdentifier));
        var parameterSql = string.Join(", ", Enumerable.Repeat("?", columns.Count));
        var insertSql = $"INSERT INTO {QuoteAccessIdentifier(tableName)} ({columnSql}) VALUES ({parameterSql})";
        var sourceColumns = BuildResolvedColumnSources(columns, rows[0]);

        Dictionary<string, string>? failedRow = null;
        try
        {
            for (var offset = 0; offset < rows.Count; offset += AccessTransactionBatchSize)
            {
                using var transaction = connection.BeginTransaction();
                await using var command = new OdbcCommand(insertSql, connection, transaction);
                foreach (var _ in columns)
                {
                    command.Parameters.Add(string.Empty, OdbcType.NVarChar);
                }

                foreach (var row in rows.Skip(offset).Take(AccessTransactionBatchSize))
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    failedRow = row;
                    for (var columnIndex = 0; columnIndex < columns.Count; columnIndex++)
                    {
                        command.Parameters[columnIndex].Value = ResolveResolvedValue(row, sourceColumns[columnIndex]);
                    }

                    await command.ExecuteNonQueryAsync(cancellationToken);
                }

                transaction.Commit();
            }
        }
        catch (OdbcException ex)
        {
            throw new InvalidOperationException(
                $"Failed writing Access table {tableName}. Columns: {string.Join(", ", columns)}. " +
                $"Sample values: {BuildResolvedRowPreview(failedRow ?? rows.First(), columns)}. " +
                $"ODBC error: {ex.Message}",
                ex);
        }
    }

    private static async Task InsertResolvedRowsAsync(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<AccessColumnSchema> columns,
        IReadOnlyList<Dictionary<string, string>> rows,
        CancellationToken cancellationToken)
    {
        if (rows.Count == 0)
        {
            return;
        }

        var columnSql = string.Join(", ", columns.Select(column => QuoteAccessIdentifier(column.Name)));
        var parameterSql = string.Join(", ", Enumerable.Repeat("?", columns.Count));
        var insertSql = $"INSERT INTO {QuoteAccessIdentifier(tableName)} ({columnSql}) VALUES ({parameterSql})";
        var sourceColumns = BuildResolvedColumnSources(columns.Select(column => column.Name).ToList(), rows[0]);

        Dictionary<string, string>? failedRow = null;
        try
        {
            for (var offset = 0; offset < rows.Count; offset += AccessTransactionBatchSize)
            {
                using var transaction = connection.BeginTransaction();
                await using var command = new OdbcCommand(insertSql, connection, transaction);
                foreach (var column in columns)
                {
                    var parameter = command.Parameters.Add(string.Empty, ResolveOdbcType(column.DataType));
                    if (column.DataType == typeof(string) && column.ColumnSize > 0)
                    {
                        parameter.Size = column.ColumnSize;
                    }
                }

                foreach (var row in rows.Skip(offset).Take(AccessTransactionBatchSize))
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    failedRow = row;
                    for (var columnIndex = 0; columnIndex < columns.Count; columnIndex++)
                    {
                        var column = columns[columnIndex];
                        command.Parameters[columnIndex].Value = CoerceAccessValue(ResolveResolvedValue(row, sourceColumns[columnIndex]), column);
                    }

                    await command.ExecuteNonQueryAsync(cancellationToken);
                }

                transaction.Commit();
            }
        }
        catch (OdbcException ex)
        {
            throw new InvalidOperationException(
                $"Failed writing Access table {tableName}. Columns: {string.Join(", ", columns.Select(column => column.Name))}. " +
                $"Sample values: {BuildResolvedRowPreview(failedRow ?? rows.First(), columns.Select(column => column.Name).ToList())}. " +
                $"ODBC error: {ex.Message}",
                ex);
        }
    }

    private static string BuildResolvedRowPreview(IReadOnlyDictionary<string, string> row, IReadOnlyList<string> columns)
    {
        var previewParts = new List<string>();
        foreach (var column in columns.Take(8))
        {
            previewParts.Add($"{column}={ResolveResolvedValue(row, column)}");
        }

        return string.Join("; ", previewParts);
    }

    private static string ResolveResolvedValue(IReadOnlyDictionary<string, string> row, string targetColumn)
    {
        return targetColumn.Length > 0 && row.TryGetValue(targetColumn, out var value)
            ? value
            : string.Empty;
    }

    private static List<string> BuildResolvedColumnSources(IReadOnlyList<string> targetColumns, IReadOnlyDictionary<string, string> sampleRow)
    {
        return targetColumns
            .Select(targetColumn => ResolveResolvedSourceColumn(sampleRow, targetColumn) ?? string.Empty)
            .ToList();
    }

    private static string? ResolveResolvedSourceColumn(IReadOnlyDictionary<string, string> row, string targetColumn)
    {
        if (row.ContainsKey(targetColumn))
        {
            return targetColumn;
        }

        var normalizedTarget = NormalizeAccessColumnName(targetColumn);
        foreach (var pair in row)
        {
            if (NormalizeAccessColumnName(pair.Key) == normalizedTarget)
            {
                return pair.Key;
            }
        }

        if (ResolvedAccessColumnAliases.TryGetValue(normalizedTarget, out var aliases))
        {
            foreach (var alias in aliases)
            {
                if (row.ContainsKey(alias))
                {
                    return alias;
                }

                var normalizedAlias = NormalizeAccessColumnName(alias);
                foreach (var pair in row)
                {
                    if (NormalizeAccessColumnName(pair.Key) == normalizedAlias)
                    {
                        return pair.Key;
                    }
                }
            }
        }

        return null;
    }

    private static readonly IReadOnlyDictionary<string, string[]> ResolvedAccessColumnAliases =
        new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
        {
            ["tdate"] = new[] { "Date" },
            ["wtrrate"] = new[] { "Water_Rate" },
            ["mfwhp"] = new[] { "TubingPressure" },
            ["cfwhp"] = new[] { "CasingPressure" },
            ["msiwhp"] = new[] { "Sitp" },
            ["msibhp"] = new[] { "Sibhp" },
            ["bhpz"] = new[] { "Bhpz" },
            ["tcomment"] = new[] { "Notes" }
        };

    private static object CoerceAccessValue(string value, AccessColumnSchema column)
    {
        var dataType = column.DataType;
        if (string.IsNullOrWhiteSpace(value))
        {
            return DBNull.Value;
        }

        if (dataType == typeof(string))
        {
            return column.ColumnSize > 0 && value.Length > column.ColumnSize
                ? value[..column.ColumnSize]
                : value;
        }

        if (dataType == typeof(short))
        {
            return short.TryParse(value, out var shortValue) ? shortValue : DBNull.Value;
        }

        if (dataType == typeof(int))
        {
            return int.TryParse(value, out var intValue) ? intValue : DBNull.Value;
        }

        if (dataType == typeof(long))
        {
            return long.TryParse(value, out var longValue) ? longValue : DBNull.Value;
        }

        if (dataType == typeof(decimal))
        {
            return decimal.TryParse(value, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var decimalValue) ? decimalValue : DBNull.Value;
        }

        if (dataType == typeof(double))
        {
            return double.TryParse(value, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var doubleValue) ? doubleValue : DBNull.Value;
        }

        if (dataType == typeof(float))
        {
            return float.TryParse(value, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var floatValue) ? floatValue : DBNull.Value;
        }

        if (dataType == typeof(bool) && bool.TryParse(value, out var boolValue))
        {
            return boolValue;
        }

        if (dataType == typeof(bool) && int.TryParse(value, out var boolIntValue))
        {
            return boolIntValue != 0;
        }

        if (dataType == typeof(bool))
        {
            return DBNull.Value;
        }

        if (dataType == typeof(DateTime))
        {
            if (DateTime.TryParseExact(value, "yyyy.MM.dd", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var exactDate))
            {
                return exactDate;
            }

            if (DateTime.TryParseExact(value, "MM/yyyy", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var monthYearDate))
            {
                return monthYearDate;
            }

            if (DateTime.TryParseExact(value, "M/d/yyyy h:mm:ss tt", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var timestampDate))
            {
                return timestampDate;
            }

            if (DateTime.TryParseExact(value, "M/d/yyyy", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var shortDate))
            {
                return shortDate;
            }

            if (DateTime.TryParse(value, out var parsedDate))
            {
                return parsedDate;
            }

            return DBNull.Value;
        }

        return value;
    }

    private static OdbcType ResolveOdbcType(Type dataType)
    {
        if (dataType == typeof(short))
        {
            return OdbcType.SmallInt;
        }

        if (dataType == typeof(int))
        {
            return OdbcType.Int;
        }

        if (dataType == typeof(long))
        {
            return OdbcType.BigInt;
        }

        if (dataType == typeof(decimal))
        {
            return OdbcType.Decimal;
        }

        if (dataType == typeof(double))
        {
            return OdbcType.Double;
        }

        if (dataType == typeof(float))
        {
            return OdbcType.Real;
        }

        if (dataType == typeof(bool))
        {
            return OdbcType.Bit;
        }

        if (dataType == typeof(DateTime))
        {
            return OdbcType.DateTime;
        }

        return OdbcType.NVarChar;
    }

    private static async Task WriteDictionaryTableAsync(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<Dictionary<string, object>> rows,
        CancellationToken cancellationToken,
        bool preferExistingSchema = false,
        bool extendExistingSchema = false)
    {
        var columns = BuildOrderedDictionaryColumns(rows);
        var normalizedRows = rows
            .Select(NormalizeDictionaryRow)
            .ToList();

        if (preferExistingSchema)
        {
            var existingColumnSchemas = await GetExistingAccessColumnSchemasAsync(connection, tableName, cancellationToken);
            if (existingColumnSchemas.Count > 0)
            {
                if (extendExistingSchema && columns.Count > 0)
                {
                    existingColumnSchemas = (await ExtendExistingAccessSchemaAsync(
                        connection,
                        tableName,
                        existingColumnSchemas,
                        columns,
                        cancellationToken)).ToList();
                }

                await DeleteAllRowsAsync(connection, tableName, cancellationToken);
                if (normalizedRows.Count > 0)
                {
                    await InsertResolvedRowsAsync(connection, tableName, existingColumnSchemas, normalizedRows, cancellationToken);
                }
                return;
            }
        }

        if (columns.Count == 0)
        {
            return;
        }

        await RecreateAccessTableAsync(connection, tableName, columns, cancellationToken);
        await InsertResolvedRowsAsync(connection, tableName, columns, normalizedRows, cancellationToken);
    }

    private static async Task WriteLoggedDictionaryTableAsync(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<Dictionary<string, object>> rows,
        CancellationToken cancellationToken,
        bool preferExistingSchema = false,
        bool extendExistingSchema = false)
    {
        Console.WriteLine($"Aries Access export: writing {tableName} ({rows.Count:N0} rows).");
        var startedAt = DateTime.UtcNow;
        await WriteDictionaryTableAsync(connection, tableName, rows, cancellationToken, preferExistingSchema, extendExistingSchema);
        Console.WriteLine($"Aries Access export: wrote {tableName} in {(DateTime.UtcNow - startedAt).TotalSeconds:N1}s.");
    }

    private static async Task WriteObjectTableAsync<T>(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<T> rows,
        CancellationToken cancellationToken,
        bool preferExistingSchema = false,
        bool appendToExistingSchema = false)
    {
        var (columns, normalizedRows) = ConvertObjectRows(rows);
        if (preferExistingSchema)
        {
            var existingColumnSchemas = await GetExistingAccessColumnSchemasAsync(connection, tableName, cancellationToken);
            if (existingColumnSchemas.Count > 0)
            {
                normalizedRows = FilterRowsForExistingAccessTable(tableName, existingColumnSchemas, normalizedRows);

                if (!appendToExistingSchema)
                {
                    await DeleteAllRowsAsync(connection, tableName, cancellationToken);
                }

                if (normalizedRows.Count > 0)
                {
                    await InsertResolvedRowsAsync(connection, tableName, existingColumnSchemas, normalizedRows, cancellationToken);
                }
                return;
            }
        }

        if (columns.Count == 0)
        {
            return;
        }

        await RecreateAccessTableAsync(connection, tableName, columns, cancellationToken);
        await InsertResolvedRowsAsync(connection, tableName, columns, normalizedRows, cancellationToken);
    }

    private static List<Dictionary<string, string>> FilterRowsForExistingAccessTable(
        string tableName,
        IReadOnlyList<AccessColumnSchema> columns,
        List<Dictionary<string, string>> rows)
    {
        if (!string.Equals(tableName, "AC_OWNER", StringComparison.OrdinalIgnoreCase)
            && !string.Equals(tableName, "GROUPTEST", StringComparison.OrdinalIgnoreCase))
        {
            return rows;
        }

        var sourceColumns = BuildResolvedColumnSources(columns.Select(column => column.Name).ToList(), rows.FirstOrDefault() ?? new Dictionary<string, string>());
        if (string.Equals(tableName, "GROUPTEST", StringComparison.OrdinalIgnoreCase))
        {
            var hasRequiredGroupTestShape = sourceColumns.Any(sourceColumn => string.Equals(sourceColumn, "T_Date", StringComparison.OrdinalIgnoreCase))
                || rows.Any(row => row.ContainsKey("T_Date") || row.ContainsKey("TDate") || row.ContainsKey("Date"));

            if (hasRequiredGroupTestShape)
            {
                return rows;
            }

            Console.WriteLine("Aries Access export: skipping GROUPTEST rows because source rows do not match the Access group test table shape.");
            return new List<Dictionary<string, string>>();
        }

        var hasRequiredOwnerShape = sourceColumns.Any(sourceColumn => string.Equals(sourceColumn, "Propnum", StringComparison.OrdinalIgnoreCase))
            || rows.Any(row => row.ContainsKey("PROPNUM") || row.ContainsKey("OWNERNAME"));

        if (hasRequiredOwnerShape)
        {
            return rows;
        }

        Console.WriteLine("Aries Access export: skipping AC_OWNER rows because source rows do not match the Access owner table shape.");
        return new List<Dictionary<string, string>>();
    }

    private static async Task WriteLoggedObjectTableAsync<T>(
        OdbcConnection connection,
        string tableName,
        IReadOnlyList<T> rows,
        CancellationToken cancellationToken,
        bool preferExistingSchema = false,
        bool appendToExistingSchema = false)
    {
        Console.WriteLine($"Aries Access export: writing {tableName} ({rows.Count:N0} rows).");
        var startedAt = DateTime.UtcNow;
        await WriteObjectTableAsync(connection, tableName, rows, cancellationToken, preferExistingSchema, appendToExistingSchema);
        Console.WriteLine($"Aries Access export: wrote {tableName} in {(DateTime.UtcNow - startedAt).TotalSeconds:N1}s.");
    }

    private static List<string> BuildOrderedDictionaryColumns(IReadOnlyList<Dictionary<string, object>> rows)
    {
        var orderedColumns = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var row in rows)
        {
            foreach (var key in row.Keys)
            {
                if (seen.Add(key))
                {
                    orderedColumns.Add(key);
                }
            }
        }

        return orderedColumns;
    }

    private static Dictionary<string, string> NormalizeDictionaryRow(Dictionary<string, object> row)
    {
        var normalizedRow = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var pair in row)
        {
            var value = pair.Value?.ToString() ?? string.Empty;
            if (!normalizedRow.TryGetValue(pair.Key, out var existingValue))
            {
                normalizedRow[pair.Key] = value;
                continue;
            }

            if (string.IsNullOrWhiteSpace(existingValue) && !string.IsNullOrWhiteSpace(value))
            {
                normalizedRow[pair.Key] = value;
            }
        }

        return normalizedRow;
    }

    private static (List<string> Columns, List<Dictionary<string, string>> Rows) ConvertObjectRows<T>(IReadOnlyList<T> rows)
    {
        var properties = typeof(T)
            .GetProperties(System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public)
            .Where(property => property.CanRead && property.GetIndexParameters().Length == 0)
            .OrderBy(property => property.MetadataToken)
            .ToList();

        var columns = properties.Select(property => property.Name).ToList();
        var normalizedRows = new List<Dictionary<string, string>>(rows.Count);

        foreach (var row in rows)
        {
            var normalizedRow = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var property in properties)
            {
                normalizedRow[property.Name] = ConvertObjectValue(property.GetValue(row));
            }

            normalizedRows.Add(normalizedRow);
        }

        return (columns, normalizedRows);
    }

    private static string ConvertObjectValue(object? value)
    {
        return value switch
        {
            null => string.Empty,
            DateTime dateTime => dateTime.ToString("yyyy.MM.dd"),
            DateTimeOffset dateTimeOffset => dateTimeOffset.ToString("yyyy.MM.dd"),
            _ => value.ToString() ?? string.Empty
        };
    }

    private static string NormalizeAccessColumnName(string value)
    {
        return value.Replace("_", string.Empty, StringComparison.OrdinalIgnoreCase).ToUpperInvariant();
    }

    private static string QuoteAccessIdentifier(string identifier)
    {
        return "[" + identifier.Replace("]", "]]") + "]";
    }
}

public sealed class AccessExportTable
{
    public string FileName { get; set; } = string.Empty;
    public string LogicalTableName { get; set; } = string.Empty;
    public string AccessTableName { get; set; } = string.Empty;
    public List<string> OriginalColumns { get; set; } = new();
    public List<string> AccessColumns { get; set; } = new();
}

public sealed class AccessColumnSchema
{
    public string Name { get; set; } = string.Empty;
    public Type DataType { get; set; } = typeof(string);
    public int ColumnSize { get; set; }
}

public sealed class AriesAccessExportData
{
    public List<Dictionary<string, object>> MasterRows { get; set; } = new();
    public List<ProductEntity> ProductRows { get; set; } = new();
    public List<TestEntity> TestRows { get; set; } = new();
    public List<DailyExportEntity> DailyRows { get; set; } = new();
    public List<AriesEconEntity> EconRows { get; set; } = new();
    public List<LookupRow> LookupRows { get; set; } = new();
    public List<AriesSidefileEntity> SidefileRows { get; set; } = new();
    public List<AriesGroupsEntity> OwnerRows { get; set; } = new();
    public List<GroupListEntity> GroupListRows { get; set; } = new();
    public List<ScenarioRow> ScenarioRows { get; set; } = new();
    public List<SetupDataEntity> SetupDataRows { get; set; } = new();
    public List<ProjectEntity> ProjectRows { get; set; } = new();
    public List<ProjlistEntity> ProjlistRows { get; set; } = new();
    public List<SortFilterEntity> SortFilterRows { get; set; } = new();
    public List<SelFiltersEntity> SelFilterRows { get; set; } = new();
}
