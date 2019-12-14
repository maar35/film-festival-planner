using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView.TableClasses
{
    /// <summary>
    /// Film Outline Delegate, provides behaviour for the outline view in the
    /// plan analisys dialog.
    /// </summary>

    public class FilmOutlineDelegate : NSOutlineViewDelegate
    {
        #region Constants
        private const string _cellIdentifier = "FilmOutlinableCell";
        #endregion

        #region Private Variables
        private FilmOutlineDataSource _dataSource;
        private AnalyserDialogController _dialogController;
        #endregion

        #region Constructors
        public FilmOutlineDelegate(FilmOutlineDataSource datasource, AnalyserDialogController dialogController)
        {
            _dataSource = datasource;
            _dialogController = dialogController;
        }
        #endregion

        #region Override Methods

        public override NSView GetView(NSOutlineView outlineView, NSTableColumn tableColumn, NSObject item)
        {
            // Get the view cell.
            //NSTextField view = (NSTextField)outlineView.MakeView(_cellIdentifier, this);
            NSView cellView = outlineView.MakeView(tableColumn.Title, this);

            // Cast item.
            var filmOutlinable = item as IFilmOutlinable;

            // Setup view based on the column selected.
            switch (tableColumn.Title)
            {
                case "Not planned films":
                    var filmLabel = (NSTextField)cellView;
                    PopulateLabel(ref filmLabel, tableColumn.Title);
                    filmOutlinable.SetTitle(filmLabel);
                    return filmLabel;
                case "Rating":
                    var ratingLabel = (NSTextField)cellView;
                    PopulateLabel(ref ratingLabel, tableColumn.Title);
                    filmOutlinable.SetRating(ratingLabel);
                    return ratingLabel;
                case "Go":
                    NSClipView control = (NSClipView)cellView;
                    PopulateControl(ref control, tableColumn);
                    filmOutlinable.SetGo(control);
                    return control;
                case "Info":
                    var infoLabel = (NSTextField)cellView;
                    PopulateLabel(ref infoLabel, tableColumn.Title);
                    filmOutlinable.SetInfo(infoLabel);
                    return infoLabel;
            }
            return cellView;
        }
        #endregion

        #region Private Methods to populate the cell view
        // This pattern allows you reuse existing views when they are no-longer in use.
        // If the returned view is null, you instance up a new view.
        // If a non-null view is returned, you modify it enough to reflect the new data.

        private void PopulateLabel(ref NSTextField label, string identifier)
        {
            if (label == null)
            {
                label = new NSTextField
                {
                    AutoresizingMask = NSViewResizingMask.WidthSizable,
                    Identifier = identifier,
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = false
                };
            }
        }

        private void PopulateControl(ref NSClipView control, NSTableColumn column)
        {
            if (control == null)
            {
                var side = column.TableView.RowHeight;
                control = new NSClipView
                {
                    Identifier = column.Identifier,
                    DrawsBackground = false,
                    AutoresizingMask = NSViewResizingMask.WidthSizable,
                    Frame = new CGRect(0, 0, side, side)
                };
            }
        }
        #endregion
    }
}