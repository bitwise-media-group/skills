using System;

namespace StyleDemo;

public class ClientStore
{
    public string Load(string id)
    {
        try
        {
            Console.WriteLine("loading client " + id);
            return Fetch(id);
        }
        catch (Exception ex)
        {
            Console.WriteLine("failed: " + ex.Message);
            throw ex;
        }
    }

    private static string Fetch(string id) => id;
}
