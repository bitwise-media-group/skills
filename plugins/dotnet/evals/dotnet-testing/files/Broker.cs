using System;

namespace TestDemo;

public sealed class TokenBroker(IClock clock)
{
    public bool IsExpired(DateTimeOffset expiresAt) => clock.UtcNow() >= expiresAt;
}
