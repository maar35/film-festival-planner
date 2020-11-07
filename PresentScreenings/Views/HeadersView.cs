using System;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Headers view, provides a time-bar which helps to visually recognize
    /// start time and end time of the screenings.
    /// </summary>

    public class HeadersView
    {
        #region Private Members
        private NSTableColumn _screensColumn;
        private NSTableColumn _screeningsColumn;
        private ScreeningsTableView _superView;
        private static nfloat _horzPixelsPerSpace = (nfloat)3.7;
        private static nfloat _hourTextWidth = (nfloat)14.4;
        private nfloat _horzTextPixels;
        #endregion

        #region Constructors
        public HeadersView(NSTableColumn screensColumn, NSTableColumn screeningsColumn, ScreeningsTableView superview)
        {
            _screensColumn = screensColumn;
            _screeningsColumn = screeningsColumn;
            _superView = superview;
        }
        #endregion

        #region Draw mehods
        public void DrawCurrDay(ScreeningsPlan plan)
        {
            _screensColumn.Title = Screening.DayString(plan.CurrDay);
        }

        public void DrawHours()
        {
            nfloat horzPosition = ScreeningsTableView.XHourStart;
            _screeningsColumn.HeaderCell.Title = "";
            _horzTextPixels = 0;
            _screeningsColumn.HeaderCell.Title += SpacesToPosition(horzPosition);
            for (int hour = ScreeningsTableView.FirstDisplayedHour; hour <= ScreeningsTableView.LastDisplayedHour; hour++)
            {
                string text = string.Format("{0:d2}:00", hour);
                _screeningsColumn.HeaderCell.Title += text;
                _horzTextPixels += _hourTextWidth;
                horzPosition += _superView.HorzPixelsPerHour;
                _screeningsColumn.HeaderCell.Title += SpacesToPosition(horzPosition);
            }
        }
        #endregion

        #region Private Methods
        private string SpacesToPosition(nfloat horzPosition)
        {
            string spaces = "";
            while (_horzTextPixels < horzPosition)
            {
                spaces += " ";
                _horzTextPixels += _horzPixelsPerSpace;
            }
            return spaces;
        }
        #endregion
    }
}
