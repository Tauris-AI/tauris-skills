using Tauris.Odbc.Common.Objects.AriesEntities;
using Tauris.Odbc.Objects;
using Tauris.PhdWin.Common.Models;
using Tauris.PhdWin.Endpoints.Project;
using Tauris.PhdWin.Entities;
using Tauris.PhdWin.Server.Endpoints.Imports;
using Tauris.Shared;
using Tauris.Shared.Models;
using Dapper;
using System.Globalization;
using Microsoft.Extensions.Options;
using Npgsql;
using SetupDataEntity = Tauris.PhdWin.Server.Endpoints.ModelVariable.SetupDataEntity;

namespace Tauris.PhdWin.Server.Endpoints.Aries;

public interface IImportScopedAriesService
{
    Task<ApiResponse?> ValidateLeaseAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default);
    Task<List<short>> GetLeaseIdsAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task<List<short>> GetExportLeaseIdsAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task<List<Dictionary<string, object>>> GetMasterTableAsync(Guid jobId, short? leaseId, CancellationToken cancellationToken = default);
    Task<LeaseScopedActualTables> GetLeaseScopedActualTablesAsync(Guid jobId, IReadOnlyCollection<short> leaseIds, CancellationToken cancellationToken = default);
    Task<List<ProductEntity>> GetProductTableAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default);
    Task<List<TestEntity>> GetTestTableAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default);
    Task<List<DailyExportEntity>> GetDailyTableAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default);
    Task<List<AriesLookupRepository.LookupRow>> GetLookupTableAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task<List<AriesGroupsEntity>> GetGroupsTableAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task<List<GroupListEntity>> GetGroupListTableAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task<List<ScenarioEntity>> GetScenarioTableAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task<List<SetupDataEntity>> GetSetupDataTableAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task<List<ProjectEntity>> GetProjectTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default);
    Task<List<ProjlistEntity>> GetProjlistTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default);
    Task<List<SortFilterEntity>> GetSortFiltersTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default);
    Task<List<SelFiltersEntity>> GetSelFiltersTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default);
}

public sealed class ImportScopedAriesService : IImportScopedAriesService
{
    private const string DefaultProjectKey = "00_RSV_CAT";

    private readonly IImportWorkspaceReaderService _workspaceReader;
    private readonly IImportJobService _importJobService;
    private readonly PostgresImportOptions _postgresOptions;

    public ImportScopedAriesService(
        IImportWorkspaceReaderService workspaceReader,
        IImportJobService importJobService,
        IOptions<PostgresImportOptions> postgresOptions)
    {
        _workspaceReader = workspaceReader;
        _importJobService = importJobService;
        _postgresOptions = postgresOptions.Value;
    }

    public async Task<ApiResponse?> ValidateLeaseAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default)
    {
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);
        if (leases.Any(l => l.Lse_id == leaseId))
        {
            return null;
        }

        return new ApiResponse
        {
            Success = false,
            Messages = new List<string> { $"Lse Id {leaseId} does not exist in staged import job {jobId}" }
        };
    }

    public async Task<List<short>> GetLeaseIdsAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);
        return leases
            .Select(lease => lease.Lse_id)
            .Distinct()
            .OrderBy(leaseId => leaseId)
            .ToList();
    }

    public async Task<List<short>> GetExportLeaseIdsAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        var job = await _importJobService.GetAsync(jobId, cancellationToken);
        if (!string.IsNullOrWhiteSpace(job?.AriesResolvedSchema) && !string.IsNullOrWhiteSpace(_postgresOptions.ConnectionString))
        {
            try
            {
                await using var connection = new NpgsqlConnection(_postgresOptions.ConnectionString);
                await connection.OpenAsync(cancellationToken);

                var leaseIds = await connection.QueryAsync<short>(
                    $"""
                    select distinct lease_id
                    from {QuoteIdentifier(job.AriesResolvedSchema)}.{QuoteIdentifier("aries_property")}
                    order by lease_id;
                    """);

                return leaseIds.ToList();
            }
            catch (NpgsqlException)
            {
            }
        }

        return await GetLeaseIdsAsync(jobId, cancellationToken);
    }

    public async Task<List<Dictionary<string, object>>> GetMasterTableAsync(Guid jobId, short? leaseId, CancellationToken cancellationToken = default)
    {
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);
        var productNames = await _workspaceReader.ReadTableAsync<ProductnamesEntity>(jobId, "PHD_PRODUCTNAMES", cancellationToken);
        var ownerRows = await _workspaceReader.ReadTableAsync<OwnerEntity>(jobId, "PHD_OWNER", cancellationToken);
        var groups = await _workspaceReader.ReadTableAsync<GroupsEntity>(jobId, "PHD_GROUPS", cancellationToken);
        var classes = await _workspaceReader.ReadTableAsync<ClassEntity>(jobId, "PHD_CLASS", cancellationToken);
        var categories = await _workspaceReader.ReadTableAsync<CategoryEntity>(jobId, "PHD_CATEGORY", cancellationToken);
        var idCodes = await _workspaceReader.ReadTableAsync<IdcodesEntity>(jobId, "PHD_IDCODES", cancellationToken);
        var idLabels = await _workspaceReader.ReadTableAsync<IdlabelsEntity>(jobId, "PHD_IDLABELS", cancellationToken);

        var filteredLeases = leaseId.HasValue
            ? leases.Where(l => l.Lse_id == leaseId.Value).ToList()
            : leases.OrderBy(l => l.Lse_id).ToList();

        var rows = new List<Dictionary<string, object>>();
        foreach (var lease in filteredLeases)
        {
            rows.Add(BuildMasterTableRow(lease, productNames, ownerRows, groups, classes, categories, idCodes, idLabels));
        }

        return rows;
    }

    private static Dictionary<string, object> BuildMasterTableRow(
        MainlseEntity lease,
        IReadOnlyList<ProductnamesEntity> productNames,
        IReadOnlyList<OwnerEntity> ownerRows,
        IReadOnlyList<GroupsEntity> groups,
        IReadOnlyList<ClassEntity> classes,
        IReadOnlyList<CategoryEntity> categories,
        IReadOnlyList<IdcodesEntity> idCodes,
        IReadOnlyList<IdlabelsEntity> idLabels)
    {
        var majorProduct = productNames.FirstOrDefault(x => x.Productcode == lease.Major_phase)?.Descr ?? string.Empty;
        var reserveClass = classes.FirstOrDefault(x => x.Cla_id == lease.Rsv_class);
        var reserveCategory = categories.FirstOrDefault(x => x.Cat_id == lease.Pdp_category);
        var partnerNames = ownerRows
            .Where(x => x.Lse_id == lease.Lse_id && x.Seq == 1)
            .Join(groups, owner => owner.Grp_id, group => group.Grp_id, (_, group) => group.Grp_desc)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
        var reserveClassText = BuildReserveClassText(lease, reserveClass);
        var reserveCategoryText = BuildReserveCategoryText(lease, reserveCategory);

        var row = new Dictionary<string, object>
        {
            { "dbskey", "168888" },
            { "propnum", LeaseViewModel.GetPropnumForLeaseId(lease.Lse_id) },
            { "seq", lease.Lse_id },
            { "major", majorProduct },
            { "prior_oil", 0 },
            { "prior_gas", 0 },
            { "prior_wtr", 0 },
            { "class", reserveClass?.Name ?? reserveClassText },
            { "rsv_class", lease.Rsv_class },
            { "rsv_class_id", lease.Rsv_class },
            { "rsv_class_name", reserveClassText },
            { "rsv_category", lease.Pdp_category },
            { "rsv_category_id", lease.Pdp_category },
            { "rsv_category_name", reserveCategoryText },
            { "rsv_cat", reserveCategoryText },
            { "rsc_sort", BuildReserveSortKey(lease, reserveClass, reserveCategory) },
            { "field", lease.Fld ?? string.Empty },
            { "reservoir", lease.Reservoir ?? string.Empty },
            { "lease", lease.Lse_name ?? string.Empty },
            { "case_name", lease.Lse_name ?? string.Empty },
            { "county", lease.County ?? string.Empty },
            { "state", lease.State ?? string.Empty },
            { "country", lease.Country ?? string.Empty },
            { "operator", lease.Oper ?? string.Empty },
            { "well", lease.Well ?? string.Empty },
            { "lse_id", lease.Lse_id },
            { "casetype", lease.CaseTypeName },
            { "partners", string.Join(';', partnerNames) },
            { "welltype", lease.WelltypeName ?? string.Empty },
            { "gasgath", lease.Gasgath ?? string.Empty },
            { "oilgath", lease.Oilgath ?? string.Empty },
            { "prod_start", lease.Sop_dttm.ToString("yyyy.MM.dd") },
            { "prod_end", lease.Eop_dttm.ToString("yyyy.MM.dd") },
            { "depth", lease.Td },
            { "latitude", lease.Lat },
            { "longitude", lease.Long },
            { "location", lease.Location ?? string.Empty },
            { "gradient", lease.Gradient },
            { "tubingdiam", lease.Tubingid },
            { "tai_exclude", lease.Exclsum == 1 ? "1" : string.Empty },
            { "exclsum", lease.Exclsum == 1 ? "true" : "false" },
            { "exclcash", lease.Exclcash == 1 ? "true" : "false" },
            { "exclvol", lease.Exclvol == 1 ? "true" : "false" }
        };

        foreach (var label in idLabels)
        {
            var value = idCodes.FirstOrDefault(x => x.Lse_id == lease.Lse_id && x.Lblnum == label.Lblnum)?.Idval ?? string.Empty;
            var sanitizedLabel = label.Idlbl.Sanitize();
            if (!string.IsNullOrWhiteSpace(sanitizedLabel))
            {
                row.TryAdd(sanitizedLabel, value);
            }
        }

        return row;
    }

    private static string BuildReserveClassText(MainlseEntity lease, ClassEntity? reserveClass)
    {
        if (!string.IsNullOrWhiteSpace(reserveClass?.Shortname))
        {
            return reserveClass.Shortname;
        }

        if (!string.IsNullOrWhiteSpace(reserveClass?.Name))
        {
            return reserveClass.Name;
        }

        return lease.Rsv_class.ToString(CultureInfo.InvariantCulture);
    }

    private static string BuildReserveCategoryText(MainlseEntity lease, CategoryEntity? reserveCategory)
    {
        if (!string.IsNullOrWhiteSpace(reserveCategory?.Shortname))
        {
            return reserveCategory.Shortname;
        }

        if (!string.IsNullOrWhiteSpace(reserveCategory?.Name))
        {
            return reserveCategory.Name;
        }

        return lease.Pdp_category.ToString(CultureInfo.InvariantCulture);
    }

    private static string BuildReserveSortKey(MainlseEntity lease, ClassEntity? reserveClass, CategoryEntity? reserveCategory)
    {
        return $"{lease.Rsv_class - 1}{lease.Pdp_category}";
    }

    public async Task<List<ProductEntity>> GetProductTableAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default)
    {
        var tables = await GetLeaseScopedActualTablesAsync(jobId, new[] { leaseId }, cancellationToken);
        return tables.ProductRows.TryGetValue(leaseId, out var rows)
            ? rows.ToList()
            : new List<ProductEntity>();
    }

    public async Task<List<TestEntity>> GetTestTableAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default)
    {
        var tables = await GetLeaseScopedActualTablesAsync(jobId, new[] { leaseId }, cancellationToken);
        return tables.TestRows.TryGetValue(leaseId, out var rows)
            ? rows.ToList()
            : new List<TestEntity>();
    }

    public async Task<List<DailyExportEntity>> GetDailyTableAsync(Guid jobId, short leaseId, CancellationToken cancellationToken = default)
    {
        var tables = await GetLeaseScopedActualTablesAsync(jobId, new[] { leaseId }, cancellationToken);
        return tables.DailyRows.TryGetValue(leaseId, out var rows)
            ? rows.ToList()
            : new List<DailyExportEntity>();
    }

    public async Task<LeaseScopedActualTables> GetLeaseScopedActualTablesAsync(Guid jobId, IReadOnlyCollection<short> leaseIds, CancellationToken cancellationToken = default)
    {
        var selectedLeaseIds = new HashSet<short>(leaseIds);
        var productRows = selectedLeaseIds.ToDictionary(leaseId => leaseId, _ => (List<ProductEntity>)new());
        var testRows = selectedLeaseIds.ToDictionary(leaseId => leaseId, _ => (List<TestEntity>)new());
        var dailyRows = selectedLeaseIds.ToDictionary(leaseId => leaseId, _ => (List<DailyExportEntity>)new());

        var monHistEntities = await _workspaceReader.ReadTableAsync<MonhistEntity>(jobId, "PHD_MONHIST", cancellationToken);
        foreach (var monhist in monHistEntities)
        {
            if (monhist.Type != 0 || !productRows.TryGetValue(monhist.Lse_id, out var leaseProductRows))
            {
                continue;
            }

            var propnum = LeaseViewModel.GetPropnumForLeaseId(monhist.Lse_id);
            for (var monthIndex = 0; monthIndex < 12; monthIndex++)
            {
                leaseProductRows.Add(new ProductEntity
                {
                    Propnum = propnum,
                    P_date = new DateTime(monhist.Year, monthIndex + 1, DateTime.DaysInMonth(monhist.Year, monthIndex + 1)).ToString("yyyy.MM.dd"),
                    Oil = monhist.Prod2[monthIndex],
                    Gas = monhist.Prod1[monthIndex],
                    Water = monhist.Prod3[monthIndex],
                    WellCount = monhist.Prod4[monthIndex],
                    Days_On = monhist.Prod5[monthIndex]
                });
            }
        }

        var dailyEntities = await _workspaceReader.ReadTableAsync<DailyEntity>(jobId, "PHD_DAILY", cancellationToken);
        foreach (var daily in dailyEntities)
        {
            if (daily.Type != 0
                || !testRows.TryGetValue(daily.Lse_id, out var leaseTestRows)
                || !dailyRows.TryGetValue(daily.Lse_id, out var leaseDailyRows))
            {
                continue;
            }

            var propnum = LeaseViewModel.GetPropnumForLeaseId(daily.Lse_id);
            leaseTestRows.Add(new TestEntity
            {
                Propnum = propnum,
                Date = daily.Tdate_dttm.ToString("yyyy.MM.dd"),
                Gas_Rate = daily.Mcfday,
                Oil_Rate = daily.Bblday,
                Water_Rate = daily.Watday,
                Choke = daily.Chokesize,
                Sibhp = daily.Sibhp,
                Sitp = daily.Sitp,
                TubingPressure = daily.Ftp,
                Z_factor = daily.Zfactor,
                Bhpz = daily.Bhpz,
                CasingPressure = daily.Csgpres,
                Notes = daily.Notes
            });

            // PHD_DAILY rows represent test/rate observations in this export path.
            // Keep them in AC_TEST and do not duplicate them into AC_DAILY as production.
        }

        return new LeaseScopedActualTables
        {
            ProductRows = productRows.ToDictionary(pair => pair.Key, pair => (IReadOnlyList<ProductEntity>)pair.Value),
            TestRows = testRows.ToDictionary(pair => pair.Key, pair => (IReadOnlyList<TestEntity>)pair.Value),
            DailyRows = dailyRows.ToDictionary(pair => pair.Key, pair => (IReadOnlyList<DailyExportEntity>)pair.Value)
        };
    }

    public async Task<List<AriesLookupRepository.LookupRow>> GetLookupTableAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        var rows = await _workspaceReader.ReadRawTableAsync(jobId, "PHD_LOOKUP", cancellationToken);
        if (rows.Count == 0)
        {
            return new List<AriesLookupRepository.LookupRow>();
        }

        var names = rows
            .Where(row => GetInt32(row, "LINETYPE") is 1 or 3)
            .Select(row => GetString(row, "NAME"))
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
            .ToList();

        var results = new List<AriesLookupRepository.LookupRow>();
        foreach (var lookupName in names)
        {
            var patternRow = rows.FirstOrDefault(row =>
                GetInt32(row, "LINETYPE") == 1
                && GetInt32(row, "SEQUENCE") == 1
                && string.Equals(GetString(row, "NAME"), lookupName, StringComparison.OrdinalIgnoreCase));

            if (patternRow is null)
            {
                continue;
            }

            var pattern = string.Concat(Enumerable.Range(0, 31).Select(index => GetString(patternRow, $"VAR{index}"))).Trim();
            var lastKeyIndex = pattern.LastIndexOf('M');
            if (lastKeyIndex < 0)
            {
                continue;
            }

            var dataRows = rows
                .Where(row => GetInt32(row, "LINETYPE") == 3
                              && string.Equals(GetString(row, "NAME"), lookupName, StringComparison.OrdinalIgnoreCase))
                .OrderBy(row => GetInt32(row, "SEQUENCE") ?? int.MaxValue);

            foreach (var dataRow in dataRows)
            {
                var vars = string.Join(' ', Enumerable.Range(0, 31).Select(index => GetString(dataRow, $"VAR{index}")))
                    .Trim();
                var offset = GetNthIndex(vars, ' ', lastKeyIndex + 1);
                if (offset < 0 || offset >= vars.Length)
                {
                    continue;
                }

                results.Add(new AriesLookupRepository.LookupRow
                {
                    Name = lookupName,
                    Key = vars[..(offset + 1)].Trim(),
                    Value = vars[(offset + 1)..].Trim()
                });
            }
        }

        return results;
    }

    public async Task<List<AriesGroupsEntity>> GetGroupsTableAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);

        return leases
            .Where(lease => lease.Casetype is 3 or 6 or 9)
            .Select(lease =>
            {
                var propnum = LeaseViewModel.GetPropnumForSpecialLease(lease.CaseTypeName, lease.Lse_id);
                return new AriesGroupsEntity
                {
                    Group_Key = $"DBSKEY='168888' AND PROPNUM='{propnum}'",
                    Group_Name = $"{propnum} | {lease.Lse_name} | {lease.Lse_id} | {lease.Fld}"
                };
            })
            .ToList();
    }

    public async Task<List<GroupListEntity>> GetGroupListTableAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);
        var economics = await _workspaceReader.ReadTableAsync<EconEntity>(jobId, "PHD_ECON", cancellationToken);
        var rptLeases = await _workspaceReader.ReadTableAsync<RptlseEntity>(jobId, "PHD_RPTLSE", cancellationToken);
        var leasesById = leases.ToDictionary(lease => lease.Lse_id);

        var groupList = new List<GroupListEntity>();

        foreach (var lease in leases.Where(lease => lease.Casetype == 9))
        {
            var econ = economics.FirstOrDefault(entry => entry.Lse_id == lease.Lse_id);
            if (econ is null)
            {
                continue;
            }

            var parentLeaseId = (short)econ.Codes[4];
            if (!leasesById.TryGetValue(parentLeaseId, out var parentLease))
            {
                continue;
            }

            groupList.Add(new GroupListEntity
            {
                Group_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForSpecialLease(lease.CaseTypeName, lease.Lse_id)}'",
                Prop_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForLeaseId(lease.Lse_id)}'",
                Weight = 1,
                Memberseq = 1,
                Member = LeaseViewModel.GetPropnumForLeaseId(lease.Lse_id)
            });

            groupList.Add(new GroupListEntity
            {
                Group_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForSpecialLease(lease.CaseTypeName, lease.Lse_id)}'",
                Prop_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForLeaseId(parentLease.Lse_id)}'",
                Weight = -1,
                Memberseq = 2,
                Member = LeaseViewModel.GetPropnumForLeaseId(parentLease.Lse_id)
            });
        }

        foreach (var parentLease in leases.Where(lease => lease.Casetype is 3 or 6))
        {
            var members = rptLeases
                .Where(rptLease => rptLease.Rpg_id == parentLease.Ecogrpid)
                .Select(rptLease => leasesById.GetValueOrDefault(rptLease.Lse_id))
                .Where(childLease => childLease is not null)
                .ToList();

            for (var index = 0; index < members.Count; index++)
            {
                var childLease = members[index]!;
                groupList.Add(new GroupListEntity
                {
                    Group_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForSpecialLease(parentLease.CaseTypeName, parentLease.Lse_id)}'",
                    Prop_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForLeaseId(childLease.Lse_id)}'",
                    Member = LeaseViewModel.GetPropnumForLeaseId(childLease.Lse_id),
                    Memberseq = index + 1,
                    Weight = 1
                });
            }
        }

        return groupList;
    }

    public async Task<List<ScenarioEntity>> GetScenarioTableAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        var groups = await _workspaceReader.ReadTableAsync<GroupsEntity>(jobId, "PHD_GROUPS", cancellationToken);
        var scenarios = new List<ScenarioEntity>();

        foreach (var group in groups)
        {
            for (var section = 1; section <= 6; section++)
            {
                scenarios.Add(new ScenarioEntity
                {
                    Data_sect = section,
                    Scen_name = group.Qualifier
                });
            }

            scenarios.Add(new ScenarioEntity
            {
                Data_sect = 7,
                Scen_name = group.Qualifier,
                Qual0 = group.Qualifier,
                Qual1 = "TAURIS"
            });

            scenarios.Add(new ScenarioEntity
            {
                Data_sect = 8,
                Scen_name = group.Qualifier,
                Qual0 = group.Qualifier,
                Qual1 = "TAURIS"
            });

            scenarios.Add(new ScenarioEntity
            {
                Data_sect = 9,
                Scen_name = group.Qualifier
            });
        }

        return scenarios;
    }

    public async Task<List<SetupDataEntity>> GetSetupDataTableAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        var titles = await _workspaceReader.ReadTableAsync<TitlesEntity>(jobId, "PHD_TITLES", cancellationToken);
        var title = titles.FirstOrDefault();
        if (title is null)
        {
            return new List<SetupDataEntity>();
        }

        var adjustedMaxEcoYears = title.Maxecoyears + title.Asof_date_dttm.Year - 2000 <= 100
            ? title.Maxecoyears + title.Asof_date_dttm.Year - 2000
            : 100;
        var deadSpaceMonths = Math.Round((title.Asof_date - new DateTime(2000, 01, 01).ToClarionDateFromDateTime()) / (365.25 / 12), 0);
        var remainingMonths = 12 - title.Asof_date_dttm.Month + 1;
        var remainingYears = Math.Round(adjustedMaxEcoYears - (deadSpaceMonths + remainingMonths) / 12, 0);

        return new List<SetupDataEntity>
        {
            new()
            {
                Secname = "TAURIS",
                Sectype = "FRAME",
                Linenumber = 1,
                Line = $"01/2000 {deadSpaceMonths},{remainingMonths},{remainingYears}*12"
            },
            new()
            {
                Secname = "TAURIS",
                Sectype = "FRAME",
                Linenumber = 4,
                Line = $"{title.Asof_date_dttm:MM/yyyy}"
            },
            new()
            {
                Secname = "TAURIS",
                Sectype = "FRAME",
                Linenumber = 2000,
                Line = $"1 -1 3 0 {adjustedMaxEcoYears}"
            }
        };
    }

    public async Task<List<ProjectEntity>> GetProjectTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default)
    {
        var groups = await _workspaceReader.ReadTableAsync<GroupsEntity>(jobId, "PHD_GROUPS", cancellationToken);
        var listRows = await _workspaceReader.ReadTableAsync<ListEntity>(jobId, "PHD_LIST", cancellationToken);
        var owners = await _workspaceReader.ReadTableAsync<OwnerEntity>(jobId, "PHD_OWNER", cancellationToken);
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);
        var leasesById = leases.ToDictionary(lease => lease.Lse_id);
        var selectedLeaseIds = leaseIds is null || leaseIds.Count == 0
            ? null
            : new HashSet<short>(leaseIds);
        var membershipsByGroupId = BuildProjectLeaseMembershipByGroup(listRows, owners, leasesById, selectedLeaseIds);
        var projects = new List<ProjectEntity>
        {
            new()
            {
                Dbskey = "168888",
                Projkey = DefaultProjectKey,
                Name = "All Cases",
                Owner = "admin",
                Pblic = "Y",
                Descriptn = "Default / All Cases",
                Query = ".",
                Rebuild = "R",
                Prop_del = "N",
                Showid_chng = "N"
            }
        };

        projects.AddRange(groups
            .Where(group => !IsAllCasesGroup(group) && membershipsByGroupId.ContainsKey(group.Grp_id))
            .OrderBy(group => group.Grp_id)
            .Select(group => new ProjectEntity
            {
                Dbskey = "168888",
                Projkey = GetProjKey(group),
                Name = group.Grp_desc.Sanitize().WithMaxLength(30),
                Owner = "admin",
                Pblic = "Y",
                Descriptn = group.Grp_desc,
                Query = ".",
                Rebuild = "R",
                Prop_del = "N",
                Showid_chng = "N"
            })
            .ToList());

        return projects;
    }

    public async Task<List<ProjlistEntity>> GetProjlistTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default)
    {
        var groups = await _workspaceReader.ReadTableAsync<GroupsEntity>(jobId, "PHD_GROUPS", cancellationToken);
        var listRows = await _workspaceReader.ReadTableAsync<ListEntity>(jobId, "PHD_LIST", cancellationToken);
        var productNames = await _workspaceReader.ReadTableAsync<ProductnamesEntity>(jobId, "PHD_PRODUCTNAMES", cancellationToken);
        var owners = await _workspaceReader.ReadTableAsync<OwnerEntity>(jobId, "PHD_OWNER", cancellationToken);
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);
        var leasesById = leases.ToDictionary(lease => lease.Lse_id);
        var selectedLeaseIds = leaseIds is null || leaseIds.Count == 0
            ? null
            : new HashSet<short>(leaseIds);
        var membershipsByGroupId = BuildProjectLeaseMembershipByGroup(listRows, owners, leasesById, selectedLeaseIds);

        var projlist = new List<ProjlistEntity>();
        var projectSequenceByKey = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        var seenMembership = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var lease in leases
                     .Where(lease => selectedLeaseIds is null || selectedLeaseIds.Contains(lease.Lse_id))
                     .OrderBy(lease => lease.Lse_id))
        {
            AddProjectMembershipRow(
                projlist,
                projectSequenceByKey,
                seenMembership,
                DefaultProjectKey,
                lease,
                productNames,
                scenario: string.Empty);
        }

        foreach (var group in groups.OrderBy(group => group.Grp_id))
        {
            if (IsAllCasesGroup(group))
            {
                continue;
            }

            if (!membershipsByGroupId.TryGetValue(group.Grp_id, out var projectLeases))
            {
                continue;
            }

            foreach (var lease in projectLeases.OrderBy(lease => lease.Lse_id))
            {
                AddProjectMembershipRow(
                    projlist,
                    projectSequenceByKey,
                    seenMembership,
                    GetProjKey(group),
                    lease,
                    productNames,
                    group.Qualifier ?? string.Empty);
            }
        }

        return projlist;
    }

    public async Task<List<SortFilterEntity>> GetSortFiltersTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default)
    {
        var projlist = await GetProjlistTableAsync(jobId, leaseIds, cancellationToken);
        var projectKeys = projlist
            .Select(row => row.Projkey)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(key => key, StringComparer.OrdinalIgnoreCase)
            .ToList();

        var sortColumns = new[]
        {
            ("RSV_CAT", "A", "Y"),
            ("CLASS", "A", "Y"),
            ("RSV_CLASS", "A", "Y"),
            ("STATE", "A", "Y"),
            ("FIELD", "A", "Y"),
            ("LEASE", "A", "N"),
            ("RSC_SORT", "A", "N"),
            ("LSE_ID", "A", "N")
        };

        var results = new List<SortFilterEntity>();
        foreach (var projkey in projectKeys)
        {
            for (var index = 0; index < sortColumns.Length; index++)
            {
                results.Add(new SortFilterEntity
                {
                    Projkey = projkey,
                    SeqNum = index,
                    TableAlias = "M",
                    TableColumn = sortColumns[index].Item1,
                    SortOrder = sortColumns[index].Item2,
                    SortBreak = sortColumns[index].Item3
                });
            }
        }

        return results;
    }

    public async Task<List<SelFiltersEntity>> GetSelFiltersTableAsync(Guid jobId, IReadOnlyCollection<short>? leaseIds = null, CancellationToken cancellationToken = default)
    {
        var groups = await _workspaceReader.ReadTableAsync<GroupsEntity>(jobId, "PHD_GROUPS", cancellationToken);
        var listRows = await _workspaceReader.ReadTableAsync<ListEntity>(jobId, "PHD_LIST", cancellationToken);
        var categories = await _workspaceReader.ReadTableAsync<CategoryEntity>(jobId, "PHD_CATEGORY", cancellationToken);
        var categoryNamesById = categories.ToDictionary(
            category => (byte)category.Cat_id,
            category => string.IsNullOrWhiteSpace(category.Shortname) ? category.Name : category.Shortname);
        var owners = await _workspaceReader.ReadTableAsync<OwnerEntity>(jobId, "PHD_OWNER", cancellationToken);
        var leases = await _workspaceReader.ReadTableAsync<MainlseEntity>(jobId, "PHD_MAINLSE", cancellationToken);
        var leasesById = leases.ToDictionary(lease => lease.Lse_id);
        var selectedLeaseIds = leaseIds is null || leaseIds.Count == 0
            ? null
            : new HashSet<short>(leaseIds);
        var membershipsByGroupId = BuildProjectLeaseMembershipByGroup(listRows, owners, leasesById, selectedLeaseIds);

        var membershipsByProject = new Dictionary<string, List<MainlseEntity>>(StringComparer.OrdinalIgnoreCase);
        foreach (var group in groups.OrderBy(group => group.Grp_id))
        {
            if (IsAllCasesGroup(group))
            {
                continue;
            }

            if (!membershipsByGroupId.TryGetValue(group.Grp_id, out var projectLeases))
            {
                continue;
            }

            var projkey = GetProjKey(group);
            membershipsByProject[projkey] = projectLeases
                .OrderBy(lease => lease.Lse_id)
                .ToList();
        }

        membershipsByProject[DefaultProjectKey] = leases
            .Where(lease => selectedLeaseIds is null || selectedLeaseIds.Contains(lease.Lse_id))
            .OrderBy(lease => lease.Lse_id)
            .ToList();

        var results = new List<SelFiltersEntity>();
        foreach (var entry in membershipsByProject.OrderBy(row => row.Key, StringComparer.OrdinalIgnoreCase))
        {
            var projkey = entry.Key;
            var memberLeases = entry.Value;
            var projectFilters = new List<SelFiltersEntity>();

            projectFilters.Add(new SelFiltersEntity
            {
                Projkey = projkey,
                TableAlias = "M",
                TableColumn = "TAI_EXCLUDE",
                Operator = "is Null",
                OperatorText = string.Empty,
                AndOr = string.Empty,
                DataType = 12
            });

            var categoriesForProject = memberLeases
                .Select(lease => categoryNamesById.GetValueOrDefault(lease.Pdp_category))
                .Where(name => !string.IsNullOrWhiteSpace(name))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
                .ToList();

            if (categoriesForProject.Count > 0)
            {
                projectFilters.Add(new SelFiltersEntity
                {
                    Projkey = projkey,
                    TableAlias = "M",
                    TableColumn = "RSV_CAT",
                    Operator = "is one of",
                    OperatorText = string.Join(", ", categoriesForProject),
                    AndOr = string.Empty,
                    DataType = 12
                });
            }

            if (!string.Equals(projkey, DefaultProjectKey, StringComparison.OrdinalIgnoreCase))
            {
                var leaseIdList = memberLeases
                    .Select(lease => lease.Lse_id)
                    .Distinct()
                    .OrderBy(id => id)
                    .Select(id => id.ToString("0.00", CultureInfo.InvariantCulture))
                    .ToList();

                if (leaseIdList.Count > 0)
                {
                    projectFilters.Add(new SelFiltersEntity
                    {
                        Projkey = projkey,
                        TableAlias = "M",
                        TableColumn = "LSE_ID",
                        Operator = "is one of",
                        OperatorText = string.Join(", ", leaseIdList),
                        AndOr = string.Empty,
                        DataType = 8
                    });
                }
            }

            FinalizeProjectFilters(projectFilters);
            results.AddRange(projectFilters);
        }

        return results;
    }

    private static void FinalizeProjectFilters(List<SelFiltersEntity> projectFilters)
    {
        for (var index = 0; index < projectFilters.Count; index++)
        {
            projectFilters[index].SeqNum = index;
            if (index == projectFilters.Count - 1)
            {
                projectFilters[index].AndOr = string.Empty;
            }
            else if (string.IsNullOrWhiteSpace(projectFilters[index].AndOr))
            {
                projectFilters[index].AndOr = "And";
            }
        }
    }

    private static string GetProjKey(GroupsEntity group)
    {
        return $"{group.Qualifier.WithMaxLength(9)}{group.Grp_id}";
    }

    private static bool IsAllCasesGroup(GroupsEntity group)
    {
        return string.Equals(group.Grp_desc?.Trim(), "All Cases", StringComparison.OrdinalIgnoreCase);
    }

    private static Dictionary<short, List<MainlseEntity>> BuildProjectLeaseMembershipByGroup(
        IReadOnlyList<ListEntity> listRows,
        IReadOnlyList<OwnerEntity> owners,
        IReadOnlyDictionary<short, MainlseEntity> leasesById,
        IReadOnlySet<short>? selectedLeaseIds)
    {
        var membershipsByGroupId = new Dictionary<short, List<MainlseEntity>>();
        var seenMembership = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var groupIdsWithExplicitListRows = listRows
            .Select(row => row.Grp_id)
            .ToHashSet();

        foreach (var listRow in listRows.OrderBy(row => row.Grp_id).ThenBy(row => row.Lse_id))
        {
            if (selectedLeaseIds is not null && !selectedLeaseIds.Contains(listRow.Lse_id))
            {
                continue;
            }

            if (!leasesById.TryGetValue(listRow.Lse_id, out var lease))
            {
                continue;
            }

            AddLeaseMembership(membershipsByGroupId, seenMembership, listRow.Grp_id, lease);
        }

        foreach (var owner in owners.Where(row => row.Seq == 1).OrderBy(row => row.Grp_id).ThenBy(row => row.Lse_id))
        {
            if (groupIdsWithExplicitListRows.Contains(owner.Grp_id))
            {
                continue;
            }

            if (selectedLeaseIds is not null && !selectedLeaseIds.Contains(owner.Lse_id))
            {
                continue;
            }

            if (!leasesById.TryGetValue(owner.Lse_id, out var lease))
            {
                continue;
            }

            AddLeaseMembership(membershipsByGroupId, seenMembership, owner.Grp_id, lease);
        }

        return membershipsByGroupId;
    }

    private static void AddLeaseMembership(
        Dictionary<short, List<MainlseEntity>> membershipsByGroupId,
        HashSet<string> seenMembership,
        short groupId,
        MainlseEntity lease)
    {
        var membershipKey = $"{groupId}|{lease.Lse_id}";
        if (!seenMembership.Add(membershipKey))
        {
            return;
        }

        if (!membershipsByGroupId.TryGetValue(groupId, out var members))
        {
            members = new List<MainlseEntity>();
            membershipsByGroupId[groupId] = members;
        }

        members.Add(lease);
    }

    private static void AddProjectMembershipRow(
        List<ProjlistEntity> projlist,
        Dictionary<string, int> projectSequenceByKey,
        HashSet<string> seenMembership,
        string projkey,
        MainlseEntity lease,
        IReadOnlyList<ProductnamesEntity> productNames,
        string scenario)
    {
        var propnum = LeaseViewModel.GetPropnumForLeaseId(lease.Lse_id);
        var membershipKey = $"{projkey}|{propnum}";
        if (!seenMembership.Add(membershipKey))
        {
            return;
        }

        projectSequenceByKey.TryGetValue(projkey, out var currentSequence);
        currentSequence++;
        projectSequenceByKey[projkey] = currentSequence;

        var major = productNames.FirstOrDefault(product => product.Productcode == lease.Major_phase)?.Descr ?? string.Empty;

        projlist.Add(new ProjlistEntity
        {
            Intkey = propnum,
            Projkey = projkey,
            Propkey = propnum,
            Propname = lease.Lse_name ?? string.Empty,
            Entitytype = "P",
            Selected = "Y",
            Breaklevel = 0,
            Projseq = currentSequence,
            Major = major,
            Scenario = scenario
        });
    }

    private static string GetString(Dictionary<string, System.Text.Json.JsonElement> row, string key)
    {
        var match = row.Keys.FirstOrDefault(candidate => string.Equals(candidate, key, StringComparison.OrdinalIgnoreCase));
        if (match is null)
        {
            return string.Empty;
        }

        var value = row[match];
        if (value.ValueKind is System.Text.Json.JsonValueKind.Null or System.Text.Json.JsonValueKind.Undefined)
        {
            return string.Empty;
        }

        return value.ValueKind == System.Text.Json.JsonValueKind.String
            ? value.GetString() ?? string.Empty
            : value.ToString();
    }

    private static int? GetInt32(Dictionary<string, System.Text.Json.JsonElement> row, string key)
    {
        var text = GetString(row, key);
        return int.TryParse(text, out var value) ? value : null;
    }

    private static int GetNthIndex(string source, char target, int occurrence)
    {
        var count = 0;
        for (var index = 0; index < source.Length; index++)
        {
            if (source[index] != target)
            {
                continue;
            }

            count++;
            if (count == occurrence)
            {
                return index;
            }
        }

        return -1;
    }

    private static string QuoteIdentifier(string value)
    {
        return "\"" + value.Replace("\"", "\"\"", StringComparison.Ordinal) + "\"";
    }
}

public sealed class LeaseScopedActualTables
{
    public IReadOnlyDictionary<short, IReadOnlyList<ProductEntity>> ProductRows { get; init; } =
        new Dictionary<short, IReadOnlyList<ProductEntity>>();

    public IReadOnlyDictionary<short, IReadOnlyList<TestEntity>> TestRows { get; init; } =
        new Dictionary<short, IReadOnlyList<TestEntity>>();

    public IReadOnlyDictionary<short, IReadOnlyList<DailyExportEntity>> DailyRows { get; init; } =
        new Dictionary<short, IReadOnlyList<DailyExportEntity>>();
}
