using System.Collections.Generic;

namespace PerfDemo;

public static class SpecBuilder
{
    public static string Build(IReadOnlyList<string> parts)
    {
        var spec = "";
        for (var i = 0; i < parts.Count; i++)
        {
            if (i > 0)
            {
                spec += ",";
            }

            spec += parts[i];
        }

        return spec;
    }
}
