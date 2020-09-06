using System;

namespace PresentScreenings.TableView
{
    public sealed class IllegalRatingException : Exception
    {
        public IllegalRatingException(string message) : base(message)
        {
        }
    }
}
