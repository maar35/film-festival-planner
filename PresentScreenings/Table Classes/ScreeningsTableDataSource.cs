using System;
using System.Collections.Generic;
//using System.Linq;
using AppKit;
//using Foundation;

namespace PresentScreenings.TableView
{
	/// <summary>
	/// Screenings table data source, povides data concerning the screenings
	/// running on given theater screens.
	/// </summary>

    public class ScreeningsTableDataSource : NSTableViewDataSource
	{
        #region Private Variables
        //private static Dictionary<bool, int> _signByAscending;
        #endregion

        #region Public Properties
        public ScreeningsPlan Plan { get; set; } = null;
        public List<Screen> Screens { get; set; } = null;
		#endregion

		#region Constructors
		public ScreeningsTableDataSource()
		{
            //_signByAscending = new Dictionary<bool, int> { };
            //_signByAscending[true] = 1;
            //_signByAscending[false] = -1;
        }
        #endregion

        #region Override Methods
        public override nint GetRowCount(NSTableView tableView)
		{
            return Plan.CurrDayScreens.Count;
		}
        #endregion
    }
}
