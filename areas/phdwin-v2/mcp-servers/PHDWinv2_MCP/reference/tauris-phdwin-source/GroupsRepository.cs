using Newtonsoft.Json;
using Tauris.Odbc.Common.Endpoints.Schema;
using Tauris.PhdWin.Common.Models;
using Tauris.PhdWin.Data;
using Tauris.PhdWin.Entities;

namespace Tauris.PhdWin.Server.Endpoints.Aries;

public class GroupsRepository
{
	// Add the Unit, Platform and Incremental cases to the AC_PROPERTY Table first -- Done

	private readonly SchemaService _schemaService;
	private readonly PhdWinRepository<MainlseEntity> _mainlseRepository;
	private readonly PhdWinRepository<EconEntity> _econRepository;
	private readonly PhdWinRepository<RptlseEntity> _rptlseRepository;
	private readonly PhdWinRepository<GroupsEntity> _groupsRepository;
	private readonly ILogger<GroupsRepository> _logger;

    public GroupsRepository(SchemaService schemaService, PhdWinRepository<MainlseEntity> mainlseRepository, PhdWinRepository<EconEntity> econRepository,
        PhdWinRepository<RptlseEntity> rptlseRepository, ILogger<GroupsRepository> logger, PhdWinRepository<GroupsEntity> groupsRepository)
    {
        _schemaService = schemaService;
        _mainlseRepository = mainlseRepository;
        _econRepository = econRepository;
        _rptlseRepository = rptlseRepository;
        _logger = logger;
        _groupsRepository = groupsRepository;
    }

    public async IAsyncEnumerable<ScenarioEntity> GetScenarioTable()
	{
		// Only want distinct owners so we get seq = 1.
		var groups = await _groupsRepository.GetAll();
        foreach (var group in groups)
        {
            for (int i = 1; i <= 6; i++)
			{
				yield return new ScenarioEntity()
				{
					Data_sect = i,
					Scen_name = group.Qualifier,
                };
			}
            yield return new ScenarioEntity()
            {
                Data_sect = 7,
                Scen_name = group.Qualifier,
                Qual0 = group.Qualifier,
                Qual1 = "TAURIS"
            };
            yield return new ScenarioEntity()
            {
                Data_sect = 8,
                Scen_name = group.Qualifier,
                Qual0 = group.Qualifier,
                Qual1 = "TAURIS"
            };
            yield return new ScenarioEntity()
            {
                Data_sect = 9,
                Scen_name = group.Qualifier,
            };
        }
	}

    public async IAsyncEnumerable<AriesGroupsEntity> GetGroupsTable()
	{
		var leases = await GetPlatformUnitIncrementalLeases();
		foreach (var lease in leases) 
		{
			var propnum = LeaseViewModel.GetPropnumForSpecialLease(lease.CaseTypeName, lease.Lse_id);

            yield return new AriesGroupsEntity()
			{
				Group_Key = $"DBSKEY='168888' AND PROPNUM='{propnum}'",
				Group_Name = $"{propnum} | {lease.Lse_name} | {lease.Lse_id} | {lease.Fld}"
			};
		}
    }

	public async IAsyncEnumerable<GroupListEntity> GetGroupListTable()
	{
		// Incrementals first
		var leases = await GetIncrementalLeases();
		foreach (var lease in leases)
		{
			var econ = await _econRepository.GetById(lease.Lse_id);
			var incrParentEntity = await _mainlseRepository.GetById((int)econ.Codes[4]);

			if (incrParentEntity is null)
			{
				_logger.LogError("Lease ID {lse_id} has no child lease.", lease.Lse_id);
				continue;
			}
			var posEntity = new GroupListEntity()
			{
				Group_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForSpecialLease(lease.CaseTypeName, lease.Lse_id)}'",
                Prop_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForLeaseId(lease.Lse_id)}'",
                Weight = 1,
                Memberseq = 1,
				Member = LeaseViewModel.GetPropnumForLeaseId(lease.Lse_id)
            };

			var negEntity = new GroupListEntity()
			{
                Group_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForSpecialLease(lease.CaseTypeName, lease.Lse_id)}'",
				Prop_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForLeaseId(incrParentEntity.Lse_id)}'",
                Weight = -1,
				Memberseq = 2,
				Member = LeaseViewModel.GetPropnumForLeaseId(incrParentEntity.Lse_id)
            };

			yield return posEntity;
			yield return negEntity;
        }

		var platUnitLeases = await GetPlatAndUnitLeases();
		foreach (var parentLease in platUnitLeases)
		{
			int childIndex = 1;
			var rptleases = await _rptlseRepository.GetWithParameters(new Dictionary<string, object>() { { "rpg_id", parentLease.Ecogrpid } });
			if (!rptleases.Any())
			{
				continue;
			}
			foreach (var rptlease in rptleases)
			{
				MainlseEntity childLease = await _mainlseRepository.GetById(rptlease.Lse_id);
                yield return new GroupListEntity()
				{
					Group_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForSpecialLease(parentLease.CaseTypeName, parentLease.Lse_id)}'",
					Prop_Key = $"DBSKEY='168888' AND PROPNUM='{LeaseViewModel.GetPropnumForLeaseId(childLease.Lse_id)}'",
					Member = LeaseViewModel.GetPropnumForLeaseId(childLease.Lse_id),
					Memberseq = childIndex++,
					Weight = 1
				};

				
			}
		}
    }
    private async Task<IEnumerable<MainlseEntity>> GetPlatAndUnitLeases()
    {
        var query = "select * from \"{{phd}}\\&MAINLSE\" where casetype in (3, 6)";
        var table = await _schemaService.ExecuteQuery(query);
        return JsonConvert.DeserializeObject<IEnumerable<MainlseEntity>>(JsonConvert.SerializeObject(table));
    }


    private async Task<IEnumerable<MainlseEntity>> GetIncrementalLeases()
    {
        var query = "select * from \"{{phd}}\\&MAINLSE\" where casetype in (9)";
        var table = await _schemaService.ExecuteQuery(query);
        return JsonConvert.DeserializeObject<IEnumerable<MainlseEntity>>(JsonConvert.SerializeObject(table));
    }

    private async Task<IEnumerable<MainlseEntity>> GetPlatformUnitIncrementalLeases()
    {
        var query = "select * from \"{{phd}}\\&MAINLSE\" where casetype in (3, 6, 9)";
        var table = await _schemaService.ExecuteQuery(query);
        return JsonConvert.DeserializeObject<IEnumerable<MainlseEntity>>(JsonConvert.SerializeObject(table));
    }


}


public class ScenarioEntity
{
	public string Dbskey { get; set; } = "168888";
	public string Scen_name { get; set; } = default!;
	public int Data_sect { get; set; }
	public string Qual0 { get; set; } = "TAURIS";
    public string Qual1 { get; set; } = string.Empty;
    public string Qual2 { get; set; } = string.Empty;
    public string Qual3 { get; set; } = string.Empty;
    public string Qual4 { get; set; } = string.Empty;
    public string Qual5 { get; set; } = string.Empty;
    public string Qual6 { get; set; } = string.Empty;
    public string Qual7 { get; set; } = string.Empty;
    public string Qual8 { get; set; } = string.Empty;
    public string Qual9 { get; set; } = string.Empty;

}


public class GroupListEntity
{
	public string Group_Key { get; set; } = default!;
	public string Prop_Key { get; set; } = default!;
	public string Member { get; set; } = default!;
	public int Memberseq { get; set; }
	public string MemberName { get; set; } = string.Empty;
	public string Scenario { get; set; } = string.Empty;
	public double Weight { get; set; } = 1d;
}
public class AriesGroupsEntity
{
	public string Group_Key { get; set; } = default!;
	public string Group_Name { get; set; } = default!;
	public string Group_Type { get; set; } = "ECON";
	public string Group_Timestamp { get; set; } = DateTime.Now.ToString("yyyy.MM.dd");
    public string Dbskey { get; set; } = "168888";
    public string Scenario { get; set; } = string.Empty;
    public double Weight { get; set; } = 1d;
	public int ShowDetails { get; set; } = 0;
}