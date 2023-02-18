using System;

namespace PresentScreenings.TableView
{
    public sealed class AlertReturnsNonZeroValue : Exception
    {
        public AlertReturnsNonZeroValue(string message) : base(message)
        {
        }
    }

    public sealed class IllegalFilmInfoCategoryException : Exception
    {
        public IllegalFilmInfoCategoryException(string message) : base(message)
        {
        }
    }

    public sealed class NextAttributePartPresumptionsFailedException : Exception
    {
        public NextAttributePartPresumptionsFailedException(string message) : base(message)
        {
        }
    }

    public sealed class TooManyLoopsWhilePlanningException : Exception
    {
        public TooManyLoopsWhilePlanningException(string message) : base(message)
        {
        }
    }
}
