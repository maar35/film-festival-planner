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
        #region Private Members
        static nfloat _xHourDefault = 120;
        nfloat _xHour;
        static nfloat _yMargin = 2;
        static nfloat _yLine = 17;
        static int _linesPerScreening = 2;
        static nfloat _xHourStart = _yLine *_linesPerScreening;
        static int _firstDisplayedHour = 9;
        static int _lastDisplayedHour = 24;
        ScreeningsView _screeningsView;
        HeadersView _headersView;
        #endregion

        #region Properties
        public nfloat HorzPixelsPerHour => _xHour;
        public static int FirstDisplayedHour => _firstDisplayedHour;
        public static int LastDisplayedHour => _lastDisplayedHour;
        public static nfloat VertPixelsPerLine => _yLine;
        public static nfloat XHourStart => _xHourStart;
        public static nfloat VertPixelsPerScreening => VertPixelsPerLine * _linesPerScreening;
        public static nfloat VertPixelsPerRow = VertPixelsPerScreening + _yMargin;
        public ScreeningsView ScreeningsView => _screeningsView;
        public HeadersView HeadersView => _headersView;
        public static nfloat YMargin { get => _yMargin; set => _yMargin = value; }
        #endregion

        #region Contructors
        public ScreeningsTableView(ViewController controller, NSTableColumn screensColumn, NSTableColumn screeningsColumn)
        {
            _screeningsView = new ScreeningsView(controller, this);
            _headersView = new HeadersView(screensColumn, screeningsColumn, this);
            _xHour = _xHourDefault;
        }
        #endregion

        #region Public Methods
        public void DrawHeaders(ScreeningsPlan plan)
        {
            _headersView.DrawCurrDay(plan);
            _headersView.DrawHours();
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
			return DateTime.Parse(string.Format("{0} {1}:00", date.ToShortDateString(), _firstDisplayedHour));
		}
		#endregion
	}
}
