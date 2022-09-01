using System;
using AppKit;
using System.Collections.Generic;
using Foundation;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film table delegate, provides the behaviour for the film ratings dialog.
    /// </summary>

    public class FilmTableDelegate : NSTableViewDelegate
    {
        #region Constants
        private const float _titleWidth = 260;
        private const string _cellIdentifier = "FilmCell";
        private const string _rowIdentifier = "FilmRow";
        #endregion

        #region Private Variables
        private FilmTableDataSource _dataSource;
        private ViewController _controller;
        private FilmRatingDialogController _dialogController;
        #endregion

        #region Constructors
        public FilmTableDelegate(FilmTableDataSource datasource, ViewController controller, FilmRatingDialogController dialog)
        {
            _dataSource = datasource;
            _controller = controller;
            _dialogController = dialog;
        }
        #endregion

        #region Override Methods
        public override nint GetNextTypeSelectMatch(NSTableView tableView, nint startRow, nint endRow, string searchString)
        {
            nint row = startRow;
            nint length = _dataSource.Films.Count;
            List<Film> films = _dataSource.Films.GetRange((int)startRow, (int)(length - startRow));
            films.AddRange(_dataSource.Films.GetRange(0, (int)startRow));
            foreach (Film film in films)
            {
                string[] titleWords;
                if (FilmRatingDialogController.TypeMatchFromBegin)
                {
                    titleWords = new string[] { film.Title };
                }
                else
                {
                    titleWords = film.Title.Split(' ');
                }
                foreach (var word in titleWords)
                {
                    if (word.StartsWith(searchString, StringComparison.CurrentCultureIgnoreCase))
                    {
                        return row % length;
                    }
                }

                // Increment row counter.
                ++row;
            }

            // If not found select the first row.
            return 0;
        }

        public override void SelectionDidChange(NSNotification notification)
        {
            // Don't call base.SelectionDidChange(notification).

            _dialogController.SetFilmRatingDialogButtonStates();
        }

        public override NSView GetViewForItem(NSTableView tableView, NSTableColumn tableColumn, nint row)
        {
            // Get the cell view.
            NSView view = (NSView)tableView.MakeView(_cellIdentifier, this);

            // Get the data for the row.
            Film film = _dataSource.Films[(int)row];

            // Setup view based on the column selected.
            switch (tableColumn.Title)
            {
                case "Film":
                    var filmLabel = (NSTextField)view;
                    PopulateFilm(ref filmLabel);
                    filmLabel.StringValue = film.Title;
                    tableColumn.Width = _titleWidth;
                    return filmLabel;
                case "Description":
                    var descriptionLabel = (NSTextField)view;
                    PopulateDescription(ref descriptionLabel);
                    descriptionLabel.AttributedStringValue = FilmInfo.InfoString(film);
                    return descriptionLabel;
                case "Duration":
                    var durationLabel = (NSTextField)view;
                    PopulateDuration(ref durationLabel);
                    durationLabel.StringValue = film.DurationString;
                    durationLabel.TextColor = DurationTextColor(film.Duration);
                    return durationLabel;
                case "#Screenings":
                    var screeningCountLabel = (NSTextField)view;
                    PopulateScreeningCount(ref screeningCountLabel);
                    int screeningCount = film.FilmScreenings.Count;
                    screeningCountLabel.StringValue = screeningCount.ToString();
                    screeningCountLabel.TextColor = ScreeningCountTextColor(screeningCount);
                    return screeningCountLabel;
                case "Subsection":
                    var subsectionControl = (SubsectionControl)view;
                    PupulateSubsection(ref subsectionControl, film, tableView, tableColumn);
                    subsectionControl.ToolTip = film.SubsectionDescription;
                    subsectionControl.Film = film;
                    subsectionControl.Enabled = film.Subsection != null;
                    return subsectionControl;
                default:
                    if (ScreeningInfo.FilmFans.Contains(tableColumn.Title))
                    {
                        var fanRatingField = (NSTextField)view;
                        PopulateFilmFanFilmRating(ref fanRatingField);
                        fanRatingField.StringValue = ViewController.GetFilmFanFilmRating(film, tableColumn.Title).ToString();
                        fanRatingField.Tag = row;
                        return fanRatingField;
                    }
                    break;
            }
            return view;
        }

        public override NSTableRowView CoreGetRowView(NSTableView tableView, nint row)
        {
            var rowView = tableView.MakeView(_rowIdentifier, this);
            if (rowView == null)
            {
                rowView = new FilmTableRowView();
                rowView.Identifier = _rowIdentifier;
            }
            return rowView as NSTableRowView;
        }
        #endregion

        #region Private Methods to populate the cell view
        // This pattern allows you reuse existing views when they are no-longer in use.
        // If the returned view is null, you instance up a new view.
        // If a non-null view is returned, you modify it enough to reflect the new data.

        private void PopulateFilm(ref NSTextField field)
        {
            if (field == null)
            {
                field = new NSTextField
                {
                    Identifier = _cellIdentifier,
                    BackgroundColor = NSColor.Clear,
                    TextColor = NSColor.Black,
                    Bordered = false,
                    Selectable = false,
                    Editable = false,
                    Alignment = NSTextAlignment.Left,
                    LineBreakMode = NSLineBreakMode.TruncatingMiddle,
                };
            }
        }

        private void PopulateDuration(ref NSTextField field)
        {
            if (field == null)
            {
                field = new NSTextField
                {
                    Identifier = _cellIdentifier,
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = false,
                    Alignment = NSTextAlignment.Left,
                };
            }
        }

        private void PopulateDescription(ref NSTextField field)
        {
            if (field == null)
            {
                field = new NSTextField
                {
                    Identifier = "Description",
                    BackgroundColor = NSColor.Clear,
                    TextColor = NSColor.Black,
                    Bordered = false,
                    Selectable = true,
                    Editable = false,
                    Alignment = NSTextAlignment.Left,
                    LineBreakMode = NSLineBreakMode.TruncatingTail,
                };
            }
        }

        private void PopulateScreeningCount(ref NSTextField field)
        {
            if (field == null)
            {
                field = new NSTextField
                {
                    Identifier = "#Screenings",
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = false,
                    Alignment = NSTextAlignment.Center,
                };
            }
        }

        private void PupulateSubsection(ref SubsectionControl control, Film film, NSTableView tableView, NSTableColumn tableColumn)
        {
            if (control == null)
            {
                var h = tableView.RowHeight;
                var w = tableColumn.Width;
                var frame = new CGRect(0, 0, w, h);
                control = new SubsectionControl(frame, film, SubsectionControlActivated)
                {
                    Identifier = "Subsection",
                    LineBreakMode = NSLineBreakMode.TruncatingTail
                };
            }
        }

        private void PopulateFilmFanFilmRating(ref NSTextField box)
        {
            if (box == null)
            {
                box = new NSTextField()
                {
                    Identifier = _cellIdentifier,
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = false,
                    Alignment = NSTextAlignment.Right,
                };
            }
        }

        private static NSColor DurationTextColor(TimeSpan duration)
        {
            return duration < FilmRatingDialogController.MinimalDuration ? NSColor.LightGray : NSColor.Black;
        }

        private static NSColor ScreeningCountTextColor(int screeningCount)
        {
            return screeningCount == 0 ? NSColor.LightGray : NSColor.Black;
        }
        #endregion

        #region Private Methods
        private void SubsectionControlActivated(Film film)
        {
            _dialogController.ToggleSubsectionFilter(film.Subsection);
        }
        #endregion
    }
}
