using System;

namespace TestDemo;

public interface IClock
{
    DateTimeOffset UtcNow();
}
