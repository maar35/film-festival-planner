using System;
using AppKit;
using System.Collections.Generic;
using Foundation;

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

                // Increment row counter
                ++row;
            }

            // If not found select the first row
            return 0;
        }

        public override void SelectionDidChange(NSNotification notification)
        {
            //Don't call base.SelectionDidChange(notification)

            _dialogController.SetFilmRatingDialogButtonStates();
        }

        public override NSView GetViewForItem(NSTableView tableView, NSTableColumn tableColumn, nint row)
        {
            // Get the cell view
            NSTextField view = (NSTextField)tableView.MakeView(_cellIdentifier, this);

            // Get the data for the row
            Film film = _dataSource.Films[(int)row];

            // Setup view based on the column selected
            switch (tableColumn.Title)
            {
                case "Film":
                    NSTextField filmLabel = (NSTextField)view;
                    PopulateFilm(ref filmLabel);
                    filmLabel.StringValue = film.Title;
                    tableColumn.Width = _titleWidth;
                    return filmLabel;
                case "Description":
                    NSTextField descriptionLabel = (NSTextField)view;
                    PopulateDescription(ref descriptionLabel);
                    descriptionLabel.StringValue = FilmInfo.InfoString(film);
                    descriptionLabel.TextColor = TextColor(film.Duration);
                    return descriptionLabel;
                case "Duration":
                    NSTextField durationLabel = (NSTextField)view;
                    PopulateDuration(ref durationLabel);
                    durationLabel.StringValue = film.DurationString;
                    durationLabel.TextColor = TextColor(film.Duration);
                    return durationLabel;
                case "Rating":
                    RatingField myRatingField = (RatingField)view;
                    PopulateFilmFanFilmRating(ref myRatingField, film, ScreeningInfo.Me, row);
                    myRatingField.StringValue = ViewController.GetFilmFanFilmRating(film, ScreeningInfo.Me).ToString();
                    myRatingField.Tag = row;
                    return myRatingField;
                default:
                    if (ScreeningInfo.MyFriends.Contains(tableColumn.Title))
                    {
                        RatingField friendRatingField = (RatingField)view;
                        PopulateFilmFanFilmRating(ref friendRatingField, film, tableColumn.Title, row);
                        friendRatingField.StringValue = ViewController.GetFilmFanFilmRating(film, tableColumn.Title).ToString();
                        friendRatingField.Tag = row;
                        return friendRatingField;
                    }
                    break;
            }
            return view;
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
                    Bordered = false,
                    Selectable = false,
                    Editable = false,
                    Alignment = NSTextAlignment.Left,
                    LineBreakMode = NSLineBreakMode.TruncatingMiddle
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
                    Alignment = NSTextAlignment.Left
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
                    Bordered = false,
                    Selectable = true,
                    Editable = false,
                    Alignment = NSTextAlignment.Left,
                    LineBreakMode = NSLineBreakMode.TruncatingTail
                };
            }
        }

        private void PopulateFilmFanFilmRating(ref RatingField box, Film film, string filmFan, nint row)
        {
            if (box == null)
            {
                box = new RatingField(_dialogController)
                {
                    Identifier = _cellIdentifier,
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = true,
                    Alignment = NSTextAlignment.Right
                };
            }
            var ratingField = box;
            box.EditingEnded += (s, e) => HandleFilmFanRatingEditingEnded(ratingField, filmFan);
        }

        private static NSColor TextColor(TimeSpan duration)
        {
            return duration < FilmRatingDialogController.MinimalDuration ? NSColor.LightGray : NSColor.Black;
        }
        #endregion

        #region Private Methods
        private void HandleFilmFanRatingEditingEnded(NSTextField field, string filmFan)
        {
            int filmId = _dataSource.Films[(int)field.Tag].FilmId;
            _controller.SetRatingIfValid(field, r => field.StringValue, filmId, filmFan);
            _dialogController.SetFilmRatingDialogButtonStates();
        }
        #endregion
    }
}
