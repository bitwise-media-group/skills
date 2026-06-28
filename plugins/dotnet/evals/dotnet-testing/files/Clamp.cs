namespace TestDemo;

public static class Numbers
{
    public static int Clamp(int value, int low, int high)
    {
        if (value < low)
        {
            return low;
        }

        if (value > high)
        {
            return high;
        }

        return value;
    }
}
