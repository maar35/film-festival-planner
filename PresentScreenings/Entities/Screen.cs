using System;
using System.Text.RegularExpressions;

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
            OnDemand,
            OnLine
        }
        #endregion

        #region Properties
        public int ScreenId { get; }
        public string City { get; }
        public string ParseName { get; }
        public string Abbreviation { get; }
        public ScreenType Type { get; }
        public static Regex ScreenRegex => new Regex(@"(\D+)(\d*)");
        #endregion

        #region Constructors
        // Empty constructor to facilitate ListStreamer method calls.
        public Screen() { }

        // Constructor to read records from the interface file.
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

        // Constructor based on another screen, to facilitate Display Screens.
        public Screen(Screen screen, string abbreviation)
        {
            ScreenId = screen.ScreenId;
            City = screen.City;
            ParseName = screen.ParseName;
            Abbreviation = abbreviation;
            Type = screen.Type;
        }
        #endregion

        #region Override Methods
        public override bool ListFileHasHeader()
        {
            return false;
        }

        public override string ToString()
        {
            return Abbreviation;
        }
        #endregion

        #region Interface Implementations
        int IComparable.CompareTo(object obj)
        {
            return string.Compare(ToCompareString(), ((Screen)obj).ToCompareString(), StringComparison.CurrentCulture);
        }
        #endregion

        #region Private Methods
        private string ToCompareString()
        {
            string typeString = "9";
            switch (Type)
            {
                case ScreenType.Location:
                    typeString = "3";
                    break;
                case ScreenType.OnDemand:
                    typeString = "2";
                    break;
                case ScreenType.OnLine:
                    typeString = "1";
                    break;
            }
            string compareString = $"{typeString}.{Abbreviation}";
            Match match = ScreenRegex.Match(Abbreviation);
            if (match != null)
            {
                string root = match.Groups[1].Value;
                string postfix = match.Groups[2].Value;
                int number = postfix.Length == 0 ? 0 : int.Parse(postfix);
                compareString = $"{typeString}.{root}.{number:d3}";
            }
            return compareString;
        }
        #endregion
    }
}
