using System.Collections.Generic;
using System.Linq;

namespace DataDemo;

public sealed class OrderService(AppDbContext db)
{
    public List<string> CustomerNames()
    {
        var orders = db.Orders.ToList();
        var names = new List<string>();
        foreach (var order in orders)
        {
            names.Add(order.Customer.Name);
        }

        return names;
    }
}
