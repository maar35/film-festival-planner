﻿using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Holds the information of a theater screen where a movie screening plays.
    /// </summary>

    public class Screen : ListStreamer, IComparable
    {
        #region Private Members
        private enum ScreenTypeSortCode
        {
            OnLine,
            OnDemand,
            Location
        }
        private static Dictionary<ScreenType, ScreenTypeSortCode> sortCodeByType;
        public static Dictionary<string, string> screenTypeByAddressType;
        #endregion

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
        public Theater Theater { get; }
        public City City { get; }
        public string ParseName { get; }
        public string Abbreviation { get; }
        public ScreenType Type { get; }
        public static Regex ScreenRegex => new Regex(@"(\D+)(\d*)");
        #endregion

        #region Constructors
        // Static constructor.
        static Screen()
        {
            sortCodeByType = new Dictionary<ScreenType, ScreenTypeSortCode> { };
            sortCodeByType.Add(ScreenType.OnLine, ScreenTypeSortCode.OnLine);
            sortCodeByType.Add(ScreenType.OnDemand, ScreenTypeSortCode.OnDemand);
            sortCodeByType.Add(ScreenType.Location, ScreenTypeSortCode.Location);

            screenTypeByAddressType = new Dictionary<string, string> { };
            screenTypeByAddressType["1"] = "2";
            screenTypeByAddressType["2"] = "1";
            screenTypeByAddressType["3"] = "0";
        }

        // Empty constructor to facilitate ListStreamer method calls.
        public Screen() { }

        // Constructor to read records from the interface file.
        public Screen(string screenText)
        {
            // Assign the fields of the input string.
            string[] fields = screenText.Split(';');
            string screenIdString = fields[0];
            string theaterIdString = fields[1];
            ParseName = fields[2];
            string screenAbbreviation = fields[3];
            string addresType = fields[4];

            // Assign properties that need calculating.
            ScreenId = int.Parse(screenIdString);
            int theaterId = int.Parse(theaterIdString);
            Theater = (from Theater t in ScreeningsPlan.Theaters where t.TheaterId == theaterId select t).First();
            City = Theater.City;
            Abbreviation = Theater.Abbreviation + screenAbbreviation;
            string screenType = screenTypeByAddressType[addresType];
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
            int typeCode = (int)sortCodeByType[Type];
            string compareString = $"{typeCode}.{Abbreviation}";
            Match match = ScreenRegex.Match(Abbreviation);
            if (match != null)
            {
                string root = match.Groups[1].Value;
                string postfix = match.Groups[2].Value;
                int number = postfix.Length == 0 ? 0 : int.Parse(postfix);
                compareString = $"{typeCode}.{root}.{number:d3}";
            }
            return compareString;
        }
        #endregion
    }
}
