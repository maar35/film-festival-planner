using System;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screenings table view, manages one day of the film festival program,
    /// displaying theater screens vertically, the time of the day horizontally,
    /// and the screenings of the current day as rectangles, horizontally arranged
    /// according to the start and end of the screening, and vertically alligned
    /// with the its screen.
    /// </summary>

    public class ScreeningsTableView
    {
        #region Properties
        public nfloat HorzPixelsPerHour { get; } = 120;
        public static int FirstDisplayedHour { get; } = 9;
        public static int LastDisplayedHour { get; } = 24;
        public static nfloat XHourStart { get; } = ScreeningsView.HorizontalScreeningControlExtensionPixels;
        public ScreeningsView ScreeningsView { get; }
        public HeadersView HeadersView { get; }
        #endregion

        #region Contructors
        public ScreeningsTableView(ViewController controller, NSTableColumn screensColumn, NSTableColumn screeningsColumn)
        {
            ScreeningsView = new ScreeningsView(controller, this);
            HeadersView = new HeadersView(screensColumn, screeningsColumn, this);
        }
        #endregion

        #region Public Methods
        public void DrawHeaders(ScreeningsPlan plan)
        {
            HeadersView.DrawCurrDay(plan);
            HeadersView.DrawHours();
        }

        public nfloat NumberOfPixelsFromTime(DateTime start)
        {
            return XHourStart + NumberOfPixelsFromDuration(start - FirstDisplayedTime(start));
        }

        public nfloat NumberOfPixelsFromDuration(TimeSpan duration)
        {
            return HorzPixelsPerHour * (nfloat)duration.TotalMinutes / 60;
        }
		#endregion

		#region Private Methods
		static DateTime FirstDisplayedTime(DateTime date)
		{
			return DateTime.Parse(string.Format("{0} {1}:00", date.ToShortDateString(), FirstDisplayedHour));
		}
		#endregion
	}
}
