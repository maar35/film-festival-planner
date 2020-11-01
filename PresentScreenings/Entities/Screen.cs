using System;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Holds the information of a theater screen where a movie screening plays.
    /// </summary>

    public class Screen : ListStreamer, IComparable
	{
        #region Public Members
        public enum ScreenType
        {
            Location,
            OnLine
        }
        #endregion

        #region Properties
        public int ScreenId { get; }
        public string City { get; }
        public string ParseName { get; }
        public string Abbreviation { get; }
        public ScreenType Type { get; }
        #endregion

        #region Constructors
        public Screen() { }

        public Screen(string screenText)
        {
            // Assign the fields of the input string.
            string[] fields = screenText.Split(';');
            string screenId = fields[0];
            City = fields[1];
			ParseName = fields[2];
			Abbreviation = fields[3];
            string screenType = fields[4];

            // Assign properties that need calculating.
            ScreenId = int.Parse(screenId);
            Type = (ScreenType)Enum.Parse(typeof(ScreenType), screenType);
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