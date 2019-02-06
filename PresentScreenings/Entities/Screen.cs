using System;
using System.Reflection;

namespace PresentScreenings.TableView
{
	/// <summary>
	/// Holds the information of a theater screen where a movie screening plays.
	/// </summary>

    public class Screen : IComparable
	{
		#region Private Members
		readonly string _parseName;
        readonly string _abbreviation;
        #endregion

        #region Properties
        public string ParseName => _parseName;
        #endregion

        #region Constructors
        public Screen(string screenText)
		{
			string[] fields = screenText.Split(';');
			_parseName = fields[0];
			_abbreviation = fields[1];
		}
        #endregion

        #region Public Methods
        public static string Serialize(Screen screen)
        {
            return string.Join(";", screen._parseName, screen._abbreviation);
        }
		public override string ToString()
		{
			return _abbreviation;
		}

		public int CompareTo(object obj)
		{
			return string.Compare(_abbreviation, ((Screen)obj).ToString(), StringComparison.CurrentCulture);
		}
		#endregion
	}
}