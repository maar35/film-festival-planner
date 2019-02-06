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
                    return filmLabel;
                case "Rating":
                    NSTextField ratingField = (NSTextField)view;
                    PopulateRating(ref ratingField);
                    ratingField.EditingEnded += (s, e) => HandleRatingEditingEnded(ratingField);
                    ratingField.StringValue = film.Rating.ToString();
                    ratingField.Tag = row;
                    return ratingField;
                default:
                    if (ScreeningStatus.MyFriends.Contains(tableColumn.Title))
                    {
                        NSTextField friendRatingField = (NSTextField)view;
                        PopulateFriendRating(ref friendRatingField);
                        string friend = tableColumn.Title;
                        friendRatingField.EditingEnded += (s, e) => HandleFriendRatingEditingEnded(friendRatingField, friend);
                        friendRatingField.StringValue = _controller.GetFriendFilmRating(film.FilmId, friend).ToString();
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
        // If the returned view is null, you instance up a new view
        // If a non-null view is returned, you modify it enough to reflect the new data

        void PopulateFilm(ref NSTextField field)
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

        void PopulateRating(ref NSTextField box)
        {
            if (box == null)
            {
                box = new NSTextField
                {
                    Identifier = _cellIdentifier,
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = true,
                    Alignment = NSTextAlignment.Right
                };
            }
        }

        void PopulateFriendRating(ref NSTextField box)
        {
            if (box == null)
            {
                box = new NSTextField
                {
                    Identifier = _cellIdentifier,
                    BackgroundColor = NSColor.Clear,
                    Bordered = false,
                    Selectable = false,
                    Editable = true,
                    Alignment = NSTextAlignment.Right
                };
            }
        }
        #endregion

        #region Private Methods
        void HandleRatingEditingEnded(NSTextField field)
        {
            FilmRating rating = _dataSource.Films[(int)field.Tag].Rating;
            if(TrySetRating(field, ref rating))
            {
                _controller.ReloadScreeningsView();
            }
        }

        void HandleFriendRatingEditingEnded(NSTextField field, string friend)
        {
            int filmId = _dataSource.Films[(int)field.Tag].FilmId; //3
            FilmRating rating = _controller.GetFriendFilmRating(filmId, friend);
            string oldRatingValue = rating.Value;
            if(TrySetRating(field, ref rating))
            {
                _controller.ReloadScreeningsView();
            }
            if (rating.Value != oldRatingValue)
            {
                _controller.SetFriendFilmRating(filmId, friend, rating);
                _controller.ReloadScreeningsView();
            }
        }

        bool TrySetRating(NSTextField field, ref FilmRating rating)
        {
            if (!rating.SetRating(field.StringValue))
            {
                field.StringValue = rating.ToString();
                return false;
            }
            return true;
        }
        #endregion
    }
}