using System;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Holds the information of a theater screen where a movie screening plays.
    /// </summary>

    public class Screen : ListStreamer, IComparable
	{
        #region Properties
        public string ParseName { get; }
        public string Abbreviation { get; }
        #endregion

        #region Constructors
        public Screen() { }

        public Screen(string screenText)
        {
			string[] fields = screenText.Split(';');
			ParseName = fields[0];
			Abbreviation = fields[1];
		}
        #endregion

        #region Override Methods
        public override bool ListFileHasHeader()
        {
            return false;
        }
        #endregion

        #region Interface Implementations
        int IComparable.CompareTo(object obj)
        {
            return string.Compare(Abbreviation, ((Screen)obj).ToString(), StringComparison.CurrentCulture);
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