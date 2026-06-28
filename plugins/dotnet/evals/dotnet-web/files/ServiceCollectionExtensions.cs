using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace WebDemo;

public static class MailingSetup
{
    public static IServiceCollection AddMailing(this IServiceCollection services, IConfiguration config)
    {
        var host = config["Smtp:Host"];
        var port = int.Parse(config["Smtp:Port"]!);
        services.AddSingleton(new Mailer(host!, port));
        return services;
    }
}

public sealed class Mailer(string host, int port)
{
    public string Host { get; } = host;
    public int Port { get; } = port;
}
