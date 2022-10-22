using System;
using System.Collections.Generic;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// A filmfestival can group the films thematically into sections.
    /// Class Section represents such sections.
    /// </summary>

    public class Section : ListStreamer
    {
        #region Private Members
        private static Dictionary<string, NSColor> _colorByName;
        #endregion

        #region Properties
        public int SectionId { get; }
        public string Name { get; }
        public NSColor Color { get; }
        #endregion

        #region Constructors
        static Section()
        {
            _colorByName = new Dictionary<string, NSColor> { };
            _colorByName["black"] = NSColor.Black;
            _colorByName["blue"] = NSColor.SystemBlue;
            _colorByName["red"] = NSColor.SystemRed;
            _colorByName["yellow"] = NSColor.SystemYellow;
        }

        public Section() { }

        public Section(string sectionText)
        {
            // Assign the fields of the input string.
            string[] fields = sectionText.Split(";");
            string sectionId = fields[0];
            Name = fields[1];
            string color = fields[2];

            // Assign properties that need calculating.
            SectionId = int.Parse(sectionId);
            Color = GetColor(color);
        }
        #endregion

        #region Override Methods
        public override bool ListFileHasHeader()
        {
            return false;
        }

        public override bool ListFileIsMandatory()
        {
            return false;
        }

        public override string ToString()
        {
            return Name;
        }
        #endregion

        #region Private Methods
        private NSColor GetColor(string colorString)
        {
            NSColor color;
            if (colorString.StartsWith("#"))
            {
                var r = Convert.ToInt32(colorString.Substring(1, 2), 16);
                var g = Convert.ToInt32(colorString.Substring(3, 2), 16);
                var b = Convert.ToInt32(colorString.Substring(5, 2), 16);
                color = NSColor.FromRgb(r, g, b);
            }
            else
            {
                color = _colorByName[colorString];
            }
            return color;
        }
        #endregion
    }
}
