using Tauris.PhdWin.Common.Models;
using Tauris.PhdWin.Data;
using Tauris.PhdWin.Endpoints.Project;
using Tauris.PhdWin.Entities;

namespace Tauris.PhdWin.Server.Endpoints.Aries;


public class ActualsRepository
{
    private readonly PhdWinRepository<MonhistEntity> _monHistRepository;
    private readonly PhdWinRepository<DailyEntity> _dailyRepository;

    public ActualsRepository(PhdWinRepository<MonhistEntity> monHistRepository, PhdWinRepository<DailyEntity> dailyRepository, IProjectRepository projectRepository)
    {
        _monHistRepository = monHistRepository;
        _dailyRepository = dailyRepository;
    }

    public async Task<List<ProductEntity>> GetProductTable(short lse_id)
    {
        List<ProductEntity> productEntities = new();
        IEnumerable<MonhistEntity> monHistEntities = await _monHistRepository.GetWithParameters(new() { { "lse_id", lse_id }, { "type", 0 } });
        if (monHistEntities.Any())
        {
            foreach (var monhist in monHistEntities)
            {
                var propnum = LeaseViewModel.GetPropnumForLeaseId(monhist.Lse_id);

                for (int i = 0; i < 12; i++)
                {
                    productEntities.Add(new ProductEntity()
                    {
                        Propnum = propnum,
                        P_date = new DateTime(monhist.Year, i + 1, DateTime.DaysInMonth(monhist.Year, i + 1)).ToString("yyyy.MM.dd"),
                        Oil = monhist.Prod2[i],
                        Gas = monhist.Prod1[i],
                        Water = monhist.Prod3[i],
                        WellCount = monhist.Prod4[i],
                        Days_On = monhist.Prod5[i]
                    });
                }
            }
        }
        return productEntities;
    }

    public async Task<List<TestEntity>> GetTestTable(short lse_id)
    {
        List<TestEntity> testEntities = new();
        var dailyEntities = await _dailyRepository.GetWithParameters(new Dictionary<string, object>() { { "lse_id", lse_id }, { "type", 0 } });

        if (!dailyEntities.Any())
        {
            return testEntities;
        }
        foreach (var daily in dailyEntities)
        {
            var propnum = LeaseViewModel.GetPropnumForLeaseId(lse_id);
            testEntities.Add(new TestEntity()
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
        }
        return testEntities;
    }

    public async Task<List<DailyExportEntity>> GetDailyTable(short lse_id)
    {
        List<DailyExportEntity> dailyExportEntities = new();
        var dailyEntities = await _dailyRepository.GetWithParameters(new Dictionary<string, object>() { { "lse_id", lse_id }, { "type", 0 } });

        if (!dailyEntities.Any())
        {
            return dailyExportEntities;
        }

        foreach (var daily in dailyEntities)
        {
            var propnum = LeaseViewModel.GetPropnumForLeaseId(lse_id);
            dailyExportEntities.Add(new DailyExportEntity()
            {
                Propnum = propnum,
                D_Date = daily.Tdate_dttm.ToString("yyyy.MM.dd"),
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
        }

        return dailyExportEntities;
    }

}

// AC_TEST
public class TestEntity
{
    public string Propnum { get; set; } = default!;
    public string Date { get; set; } = default!;
    public double Oil_Rate { get; set; }
    public double Gas_Rate { get; set; }
    public double Water_Rate { get; set; }
    public double CasingPressure { get; set; }
    public double TubingPressure { get; set; }
    public double Bhpz { get; set; }
    public double Sibhp { get; set; }
    public double Sitp { get; set; }
    public double Choke { get; set; }
    public double Z_factor { get; set; }
    public string Notes { get; set; }
}

// AC_PRODUCT
public class ProductEntity
{
    public string Propnum { get; set; } = default!;
    public string P_date { get; set; } = default!;
    public double Oil { get; set; }
    public double Gas { get; set; }
    public double Water { get; set; }
    public double WellCount { get; set; }
    public double Days_On { get; set; }
}

// AC_DAILY
public class DailyExportEntity
{
    public string Propnum { get; set; } = default!;
    public string D_Date { get; set; } = default!;
    public double Oil_Rate { get; set; }
    public double Gas_Rate { get; set; }
    public double Water_Rate { get; set; }
    public double CasingPressure { get; set; }
    public double TubingPressure { get; set; }
    public double Bhpz { get; set; }
    public double Sibhp { get; set; }
    public double Sitp { get; set; }
    public double Choke { get; set; }
    public double Z_factor { get; set; }
    public string Notes { get; set; } = string.Empty;
}
