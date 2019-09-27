using System;
using System.Reflection;

namespace PresentScreenings.TableView
{
	/// <summary>
	/// Holds the information of a theater screen where a movie screening plays.
	/// </summary>

    public class Screen : IComparable, ICanWriteList
	{
        #region Properties
        public string ParseName { get; }
        public string Abbreviation { get; }
        #endregion

        #region Constructors
        public Screen(string screenText)
		{
			string[] fields = screenText.Split(';');
			ParseName = fields[0];
			Abbreviation = fields[1];
		}
        #endregion

        #region Interface Implementations
        int IComparable.CompareTo(object obj)
        {
            return string.Compare(Abbreviation, ((Screen)obj).ToString(), StringComparison.CurrentCulture);
        }

        string ICanWriteList.Serialize()
        {
            return string.Join(";", ParseName, Abbreviation);
        }
        #endregion

        #region Public Methods
		public override string ToString()
		{
			return Abbreviation;
		}
        #endregion
    }
}