using System;

namespace DocDemo;

public static class KeyVal
{
    public static (string Key, string Value) Parse(string line)
    {
        var idx = line.IndexOf('=');
        if (idx <= 0)
        {
            throw new FormatException("missing separator");
        }

        return (line[..idx].Trim(), line[(idx + 1)..].Trim());
    }
}
