using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace Tauris.PhdWin.Server.Endpoints.Imports;

public enum ImportTemplateKind
{
    PhdWinAccess,
    AriesAccess
}

public sealed class ImportTemplateDescriptor
{
    public string Kind { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public string Source { get; set; } = string.Empty;
    public long SizeBytes { get; set; }
    public DateTime? UpdatedAtUtc { get; set; }
}

public interface IImportTemplateService
{
    Task<IReadOnlyList<ImportTemplateDescriptor>> ListAsync(CancellationToken cancellationToken = default);
    Task<ImportTemplateDescriptor> SaveOverrideAsync(ImportTemplateKind kind, IFormFile file, CancellationToken cancellationToken = default);
    ImportTemplateDescriptor GetDescriptor(ImportTemplateKind kind);
    string GetTemplatePath(ImportTemplateKind kind);
}

public sealed class ImportTemplateService : IImportTemplateService
{
    private readonly ImportStorageOptions _storageOptions;
    private readonly string _contentRootPath;

    public ImportTemplateService(IOptions<ImportStorageOptions> storageOptions, IWebHostEnvironment environment)
    {
        _storageOptions = storageOptions.Value;
        _contentRootPath = environment.ContentRootPath;
    }

    public Task<IReadOnlyList<ImportTemplateDescriptor>> ListAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        IReadOnlyList<ImportTemplateDescriptor> result = new[]
        {
            GetDescriptor(ImportTemplateKind.PhdWinAccess),
            GetDescriptor(ImportTemplateKind.AriesAccess)
        };
        return Task.FromResult(result);
    }

    public async Task<ImportTemplateDescriptor> SaveOverrideAsync(ImportTemplateKind kind, IFormFile file, CancellationToken cancellationToken = default)
    {
        var extension = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (extension is not ".accdb" and not ".mdb")
        {
            throw new InvalidOperationException("Template uploads must be .accdb or .mdb files.");
        }

        Directory.CreateDirectory(GetOverridesRootPath());
        var destinationPath = GetOverridePath(kind, extension);
        await using var stream = File.Create(destinationPath);
        await file.CopyToAsync(stream, cancellationToken);

        return GetDescriptor(kind);
    }

    public ImportTemplateDescriptor GetDescriptor(ImportTemplateKind kind)
    {
        var activePath = GetTemplatePath(kind);
        if (!File.Exists(activePath))
        {
            throw new InvalidOperationException($"The {GetDisplayName(kind)} template was not found.");
        }

        var fileInfo = new FileInfo(activePath);
        return new ImportTemplateDescriptor
        {
            Kind = ToApiKind(kind),
            DisplayName = GetDisplayName(kind),
            FileName = fileInfo.Name,
            Source = IsOverridePath(activePath) ? "uploaded" : "bundled",
            SizeBytes = fileInfo.Length,
            UpdatedAtUtc = fileInfo.Exists ? fileInfo.LastWriteTimeUtc : null
        };
    }

    public string GetTemplatePath(ImportTemplateKind kind)
    {
        foreach (var extension in new[] { ".accdb", ".mdb" })
        {
            var overridePath = GetOverridePath(kind, extension);
            if (File.Exists(overridePath))
            {
                return overridePath;
            }
        }

        return kind switch
        {
            ImportTemplateKind.PhdWinAccess => Path.GetFullPath(Path.Combine(_contentRootPath, "reference", "templates", "PHDWin_v2_tables.accdb")),
            ImportTemplateKind.AriesAccess => Path.GetFullPath(Path.Combine(_contentRootPath, "reference", "templates", "Aries_Template.accdb")),
            _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, null)
        };
    }

    private string GetOverridesRootPath()
    {
        return Path.Combine(_storageOptions.RootPath, "templates");
    }

    private string GetOverridePath(ImportTemplateKind kind, string extension)
    {
        return Path.Combine(GetOverridesRootPath(), $"{ToApiKind(kind)}{extension}");
    }

    private static string ToApiKind(ImportTemplateKind kind)
    {
        return kind switch
        {
            ImportTemplateKind.PhdWinAccess => "phdwin_access",
            ImportTemplateKind.AriesAccess => "aries_access",
            _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, null)
        };
    }

    private static string GetDisplayName(ImportTemplateKind kind)
    {
        return kind switch
        {
            ImportTemplateKind.PhdWinAccess => "PHDWin Access Template",
            ImportTemplateKind.AriesAccess => "Aries Access Template",
            _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, null)
        };
    }

    private bool IsOverridePath(string path)
    {
        var overridesRoot = Path.GetFullPath(GetOverridesRootPath());
        var fullPath = Path.GetFullPath(path);
        return fullPath.StartsWith(overridesRoot, StringComparison.OrdinalIgnoreCase);
    }
}
