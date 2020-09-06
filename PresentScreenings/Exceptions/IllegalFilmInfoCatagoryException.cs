using System;

namespace PresentScreenings.TableView
{
    public sealed class IllegalFilmInfoCatagoryException : Exception
    {
        public IllegalFilmInfoCatagoryException(string message) : base(message)
        {
        }
    }
}
