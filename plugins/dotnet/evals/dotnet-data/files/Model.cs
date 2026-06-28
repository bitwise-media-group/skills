using Microsoft.EntityFrameworkCore;

namespace DataDemo;

public sealed class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();
}

public sealed class Order
{
    public int Id { get; set; }
    public Customer Customer { get; set; } = null!;
}

public sealed class Customer
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
}
