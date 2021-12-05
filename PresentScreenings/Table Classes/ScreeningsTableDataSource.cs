using System;
using System.Collections.Generic;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screenings table data source, povides data concerning the screenings
    /// running on given theater screens.
    /// </summary>

    public class ScreeningsTableDataSource : NSTableViewDataSource
	{
        #region Public Properties
        public ScreeningsPlan Plan { get; set; } = null;
        public List<Screen> Screens { get; set; } = null;
		#endregion

		#region Constructors
		public ScreeningsTableDataSource()
		{
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
