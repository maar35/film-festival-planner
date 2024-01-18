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
        private NSColor GetColor(string colorCode)
        {
            NSColor color;
            string colorString = colorCode.ToLower();
            if (colorString.StartsWith("#"))
            {
                color = ColorView.GetColor(colorString);
            }
            else if (_colorByName.ContainsKey(colorString))
            {
                color = _colorByName[colorString];
            }
            else if (ColorView.ColorByName.ContainsKey(colorString))
            {
                color = ColorView.ColorByName[colorString];
            }
            else
            {
                color = NSColor.SystemGray;
            }
            return color;
        }
        #endregion
    }
}
