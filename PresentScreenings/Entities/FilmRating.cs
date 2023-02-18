using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film rating, provides the possibility to rate films and compare film ratings.
    /// </summary>

    public class FilmRating : IComparable
    {
        #region Private Variables
        const int _unratedIndex = 0;
        #endregion

        #region Properties
        public static List<string> Values => new List<string> { "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10" };
        private static string _valueUnrated => Values[_unratedIndex];
        public static FilmRating Unrated => new FilmRating(_valueUnrated);
        public static FilmRating LowestSuperRating => LowestPlannableRating();
        public static FilmRating MaxRating => new FilmRating(Values[Values.Count - 1]);
        public string Value { get; private set; }
        public bool IsUnrated => Value == _valueUnrated;
        #endregion

        #region Constructors
        public FilmRating(string rating)
        {
            Value = Values.Contains(rating) ? rating : _valueUnrated;
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return Value;
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

        #region Public Methods
        public bool Equals(FilmRating otherRating)
        {
            return CompareTo(otherRating) == 0;
        }

        public bool IsGreaterOrEqual(FilmRating otherRating)
        {
            return CompareTo(otherRating) >= 0;
        }

        public void Decrease()
        {
            try
            {
                Value = Values[Values.IndexOf(Value) - 1];
            }
            catch (IndexOutOfRangeException)
            {
                Value = _valueUnrated;
            }
        }
        #endregion
        #region Private Methods
        private static FilmRating LowestPlannableRating()
        {
            int index = int.Parse(AppDelegate.Config.Constants["LowestPlannableRating"]);
            return new FilmRating(Values[index]);
        }
        #endregion
    }
}
