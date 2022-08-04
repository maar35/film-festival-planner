using System;
using System.Collections.Generic;

namespace PresentScreenings.TableView.Utilities
{
    /// <summary>
    /// A dictionary-like class to make code, that uses text by bool by bool
    /// dictonaries, more readable.
    /// </summary>

    public class StringByBoolBool
    {
        #region Private Members
        private Dictionary<Tuple<bool, bool>, string> _stringByBoolBool;
        #endregion

        #region Constructors
        public StringByBoolBool()
        {
            _stringByBoolBool = new Dictionary<Tuple<bool, bool>, string> { };
        }
        #endregion

        #region Public Methods
        public string Get(bool firstBool, bool secondBool)
        {
            return _stringByBoolBool[new Tuple<bool, bool>(firstBool, secondBool)];
        }

        public void Set(bool firstBool, bool secondBool, string text)
        {
            _stringByBoolBool[new Tuple<bool, bool>(firstBool, secondBool)] = text;
        }
        #endregion
    }
}
