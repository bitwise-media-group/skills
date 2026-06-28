using System.Threading.Tasks;

namespace PerfDemo;

public sealed class Worker(IFetcher fetcher)
{
    public string Run(string id)
    {
        return fetcher.FetchAsync(id).Result;
    }
}

public interface IFetcher
{
    Task<string> FetchAsync(string id);
}
