using System;
using System.Collections;
using System.Collections.Generic;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film rating, provides the possibility to rate films and compare film ratings.
    /// </summary>

    public class FilmRating : IComparable
    {
        #region Private Variables
        const int _unratedIndex = 0;
        const int _lowestSuperRatingIndex = 8;
        #endregion

        #region Properties
        public static List<string> Values => new List<string> { "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10" };
        private static string _valueUnrated => Values[_unratedIndex];
        public static FilmRating Unrated => new FilmRating(_valueUnrated);
        public static FilmRating LowestSuperRating => new FilmRating(Values[_lowestSuperRatingIndex]);
        public string Value { get; private set; }
        public bool IsUnrated => Value == _valueUnrated;
        #endregion

        #region Constructors
        public FilmRating(string rating)
        {
            if (!SetRating(rating))
            {
                Value = _valueUnrated;
            }
        }
        #endregion

        #region override methods
        public override string ToString()
        {
            return Value;
        }
        #endregion
        
        #region Public Methods
        public bool Equals(FilmRating otherRating)
        {
            return CompareTo(otherRating) == 0;
        }

        public bool IsGreaterOrEqual(FilmRating otherRating)
        {
            return CompareTo(otherRating) >= 0;
        }

        public bool SetRating(string newRating)
        {
            if (Values.Contains(newRating))
            {
                Value = newRating;
                return true;
            }
            return false;
        }
        #endregion

        #region Interface Implementation
        public int CompareTo(object obj)
        {
            double index = Values.IndexOf(Value);
            double otherIndex = Values.IndexOf(((FilmRating)obj).Value);
            return index.CompareTo(otherIndex);
        }
        #endregion

    }
}
