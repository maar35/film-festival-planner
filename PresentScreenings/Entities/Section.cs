﻿using System;
using System.Collections.Generic;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// A section is one of the sections that a film festival may use to divide
    /// the films being screened into.
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
            _colorByName["blue"] = NSColor.Blue;
            _colorByName["red"] = NSColor.SystemRedColor;
            _colorByName["yellow"] = NSColor.SystemYellowColor;
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
            Color = _colorByName[color];
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
    }
}
