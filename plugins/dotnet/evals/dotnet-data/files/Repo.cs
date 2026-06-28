using System.Linq;

namespace DataDemo;

public sealed class OrderRepository(AppDbContext db)
{
    public Order Find(int id)
    {
        return db.Orders.First(o => o.Id == id);
    }

    public int Count()
    {
        return db.Orders.ToList().Count;
    }
}
