using System;

namespace PresentScreenings.TableView
{
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
}
