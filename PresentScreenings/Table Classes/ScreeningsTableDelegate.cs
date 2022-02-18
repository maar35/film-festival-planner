using System;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screenings table delegate, provides the behaviour for the screenings
    /// table view.
    /// </summary>

    public class ScreeningsTableDelegate : NSTableViewDelegate
    {
        #region Constants
        private const string _cellIdentifier = "PlanCell";
        private const string _rowIdentifier = "PlanRow";
        #endregion

        #region Private Members
        ScreeningsTableDataSource _dataSource;
        ScreeningsView _screeningsView;
        ViewController _controller;
        #endregion

        #region Constructors
        public ScreeningsTableDelegate(ScreeningsTableDataSource datasource, ScreeningsView view, ViewController controller)
        {
            _dataSource = datasource;
            _screeningsView = view;
            _controller = controller;
        }
        #endregion

        #region Override Methods
        public override void SelectionDidChange(NSNotification notification)
        {
            // Don't call base.SelectionDidChange(notification).

            _controller.TableView.DeselectRow(_controller.TableView.SelectedRow);
        }

        public override NSView GetViewForItem(NSTableView tableView, NSTableColumn tableColumn, nint row)
        {
            // Get the cell view
            NSView cellview = tableView.MakeView(_cellIdentifier, this);

            // Get the data for the row
            ScreeningsPlan plan = _dataSource.Plan;
            DateTime day = plan.CurrDay;
            Screen screen = plan.CurrDayScreens[(int)row];

            // Setup view based on the column selected
            switch (tableColumn.Identifier)
            {
                case "Screens":
                    NSTextField label = (NSTextField)cellview;
                    PopulateScreens(ref label);
                    label.StringValue = screen.ToString();
                    return label;
                case "Screenings":
                    NSClipView clipview = (NSClipView)cellview;
                    PopulateScreenings(ref clipview);
                    _screeningsView.DrawScreenings(clipview, plan, day, screen);
                    return clipview;
            }
            return cellview;
        }

        public override NSTableRowView CoreGetRowView(NSTableView tableView, nint row)
        {
            var rowView = tableView.MakeView(_rowIdentifier, this);
            if (rowView == null)
            {
                rowView = new ScreenigsTableRowView();
                rowView.Identifier = _rowIdentifier;
            }
            return rowView as NSTableRowView;
        }
        #endregion

        #region Private Methods to populate the cell view
        // This pattern allows you reuse existing views when they are no-longer in use.
        // If the returned view is null, you instance up a new view
        // If a non-null view is returned, you modify it enough to reflect the new data

        void PopulateScreens(ref NSTextField label)
        {
            if (label == null)
            {
                label = new NSTextField
                {
                    Identifier = _cellIdentifier,
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = false
                };
            }
        }

        void PopulateScreenings(ref NSClipView clipview)
        {
            if (clipview == null)
            {
                clipview = new NSClipView
                {
                    Identifier = _cellIdentifier,
                    DrawsBackground = false
                };
            }
        }
        #endregion
    }
}
