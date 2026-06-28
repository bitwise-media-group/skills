using System.Threading.Tasks;

namespace AsyncDemo;

public class ClientStore
{
    public Client GetClient(string id)
    {
        return Lookup(id).Result;
    }

    private static Task<Client> Lookup(string id) => Task.FromResult(new Client(id));
}

public record Client(string Id);
