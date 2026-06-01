using Tauris.Odbc.Common.Objects.AriesEntities;
using Tauris.Odbc.Objects;
using Tauris.PhdWin.Common.Models;
using Tauris.PhdWin.Data;
using Tauris.PhdWin.Endpoints.Project;
using Tauris.PhdWin.Entities;
using Tauris.PhdWin.Server.Endpoints.Forecast;
using Tauris.PhdWin.Server.Endpoints.ModelVariable;
using Tauris.PhdWin.Server.Endpoints.Ownership;
using Tauris.PhdWin.Server.Endpoints.ProjectVariable;
using Tauris.Shared.Models;
using SetupDataEntity = Tauris.PhdWin.Server.Endpoints.ModelVariable.SetupDataEntity;

namespace Tauris.PhdWin.Server.Endpoints.Aries;

public interface IAriesExportService
{
    Task<ApiResponse?> ValidateLeaseAsync(short leaseId);
    Task<List<Dictionary<string, object>>> GetMasterTableAsync(short? id);
    Task<Dictionary<string, string>> GetMasterTableDefinitionAsync();
    Task<List<AriesEconEntity>> GetLeaseEconTableAsync(short leaseId, bool noSidefile = false);
    Task<List<AriesSidefileEntity>> GetSidefileEntitiesAsync();
    Task<List<AriesSidefileEntity>> GetSidefileEntitiesAsync(short mpvId, short type);
    Task<List<AriesGroupsEntity>> GetGroupsTableAsync();
    Task<List<GroupListEntity>> GetGroupListTableAsync();
    Task<List<ProjlistEntity>> GetProjlistTableAsync();
    Task<List<ProductEntity>> GetProductTableAsync(short leaseId);
    Task<List<TestEntity>> GetTestTableAsync(short leaseId);
    Task<List<DailyExportEntity>> GetDailyTableAsync(short leaseId);
    Task<List<AriesLookupRepository.LookupRow>> GetLookupTableAsync();
    Task<List<ScenarioEntity>> GetScenarioTableAsync();
    Task<List<SetupDataEntity>> GetSetupDataTableAsync();
    Task<List<ProjectEntity>> GetProjectTableAsync();
    Task<List<SortFilterEntity>> GetSortFiltersTableAsync();
    Task<List<SelFiltersEntity>> GetSelFiltersTableAsync();
}

public sealed class AriesExportService : IAriesExportService
{
    private readonly ProjectVariableRepository _projectVariableRepository;
    private readonly ForecastViewModelRepository _forecastVMRepository;
    private readonly IProjectRepository _projectRepository;
    private readonly OwnershipRepository _ownershipRepository;
    private readonly ModelVariableRepository _modelVariableRepository;
    private readonly GroupsRepository _groupsRepository;
    private readonly ActualsRepository _actualsRepository;
    private readonly AriesLookupRepository _lookupRepository;
    private readonly PhdWinRepository<MainlseEntity> _mainlseRepository;

    public AriesExportService(
        ProjectVariableRepository projectVariableRepository,
        ForecastViewModelRepository forecastVMRepository,
        IProjectRepository projectRepository,
        OwnershipRepository ownershipRepository,
        ModelVariableRepository modelVariableRepository,
        GroupsRepository groupsRepository,
        ActualsRepository actualsRepository,
        AriesLookupRepository lookupRepository,
        PhdWinRepository<MainlseEntity> mainlseRepository)
    {
        _projectVariableRepository = projectVariableRepository;
        _forecastVMRepository = forecastVMRepository;
        _projectRepository = projectRepository;
        _ownershipRepository = ownershipRepository;
        _modelVariableRepository = modelVariableRepository;
        _groupsRepository = groupsRepository;
        _actualsRepository = actualsRepository;
        _lookupRepository = lookupRepository;
        _mainlseRepository = mainlseRepository;
    }

    public async Task<ApiResponse?> ValidateLeaseAsync(short leaseId)
    {
        var mainLseEntity = await _mainlseRepository.GetById(leaseId);
        if (mainLseEntity is not null)
        {
            return null;
        }

        return new ApiResponse
        {
            Success = false,
            Messages = new List<string> { $"Lse Id {leaseId} does not exist in this database" }
        };
    }

    public async Task<List<Dictionary<string, object>>> GetMasterTableAsync(short? id)
    {
        var rows = new List<Dictionary<string, object>>();
        await foreach (var row in _projectRepository.GetMasterTable(id))
        {
            rows.Add(row);
        }

        return rows;
    }

    public async Task<Dictionary<string, string>> GetMasterTableDefinitionAsync()
    {
        return await _projectRepository.GetMasterTableDefinition();
    }

    public async Task<List<AriesEconEntity>> GetLeaseEconTableAsync(short leaseId, bool noSidefile = false)
    {
        List<AriesEconEntity> econlines = new();
        econlines = await _forecastVMRepository.GetForecastEconlines(leaseId, null, econlines);
        econlines = await _projectVariableRepository.GetEconlines(leaseId, econlines, noSidefile);
        econlines = await _ownershipRepository.GetEconlines(leaseId, null, econlines);
        return econlines.OrderBy(x => x.Section).ThenBy(x => x.Sequence).ToList();
    }

    public async Task<List<AriesSidefileEntity>> GetSidefileEntitiesAsync()
    {
        return await _modelVariableRepository.GetSidefileEntities();
    }

    public async Task<List<AriesSidefileEntity>> GetSidefileEntitiesAsync(short mpvId, short type)
    {
        var modelVars = await _modelVariableRepository.GetModelVariable(mpvId, type);
        return modelVars?.SidefileLines ?? new List<AriesSidefileEntity>();
    }

    public async Task<List<AriesGroupsEntity>> GetGroupsTableAsync()
    {
        var groups = new List<AriesGroupsEntity>();
        await foreach (var row in _groupsRepository.GetGroupsTable())
        {
            groups.Add(row);
        }

        return groups;
    }

    public async Task<List<GroupListEntity>> GetGroupListTableAsync()
    {
        var groups = new List<GroupListEntity>();
        await foreach (var row in _groupsRepository.GetGroupListTable())
        {
            groups.Add(row);
        }

        return groups;
    }

    public async Task<List<ProjlistEntity>> GetProjlistTableAsync()
    {
        return await _ownershipRepository.GetProjlistTable();
    }

    public async Task<List<ProductEntity>> GetProductTableAsync(short leaseId)
    {
        return await _actualsRepository.GetProductTable(leaseId);
    }

    public async Task<List<TestEntity>> GetTestTableAsync(short leaseId)
    {
        return await _actualsRepository.GetTestTable(leaseId);
    }

    public async Task<List<DailyExportEntity>> GetDailyTableAsync(short leaseId)
    {
        return await _actualsRepository.GetDailyTable(leaseId);
    }

    public async Task<List<AriesLookupRepository.LookupRow>> GetLookupTableAsync()
    {
        return await _lookupRepository.GetAllLookupsAsync();
    }

    public async Task<List<ScenarioEntity>> GetScenarioTableAsync()
    {
        var scenarios = new List<ScenarioEntity>();
        await foreach (var row in _groupsRepository.GetScenarioTable())
        {
            scenarios.Add(row);
        }

        return scenarios;
    }

    public async Task<List<SetupDataEntity>> GetSetupDataTableAsync()
    {
        return await _modelVariableRepository.GetSetupDataTable();
    }

    public async Task<List<ProjectEntity>> GetProjectTableAsync()
    {
        return await _ownershipRepository.GetProjectTable();
    }

    public async Task<List<SortFilterEntity>> GetSortFiltersTableAsync()
    {
        return await _ownershipRepository.GetSortFiltersTable();
    }

    public async Task<List<SelFiltersEntity>> GetSelFiltersTableAsync()
    {
        return await _ownershipRepository.GetSelFiltersTable();
    }
}
