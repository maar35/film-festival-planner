using System;
using System.Collections.Generic;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    public class FilmOutlinable : NSObject, IFilmOutlinable
    {
        #region Properties
        public Film Film { get; }
        #endregion

        #region Constructors
        public FilmOutlinable(Film film)
        {
            Film = film;
        }
        #endregion

        #region Interface Implementations
        public List<IFilmOutlinable> FilmOutlinables { get; private set; } = new List<IFilmOutlinable> { };

        void IFilmOutlinable.Cleanup()
        {
            AnalyserDialogController.CleanupOutlinables(FilmOutlinables);
        }

        bool IFilmOutlinable.ContainsFilmOutlinables()
        {
            return FilmOutlinables.Count > 0;
        }

        void IFilmOutlinable.SetGo(NSView view)
        {
            ScreeningsView.DisposeSubViews(view);
        }

        void IFilmOutlinable.SetInfo(NSTextField view)
        {
            view.StringValue = FilmInfo.InfoString(Film);
            view.LineBreakMode = NSLineBreakMode.ByWordWrapping;
            view.BackgroundColor = NSColor.Clear;
            view.TextColor = NSColor.Text;
        }

        void IFilmOutlinable.SetRating(NSTextField view)
        {
            view.StringValue = Film.MaxRating.ToString();
        }

        void IFilmOutlinable.SetTitle(NSTextField view)
        {
            view.StringValue = Film.DurationString + " - " + Film.Title;
            view.LineBreakMode = NSLineBreakMode.TruncatingMiddle;
            view.Selectable = false;
        }
        #endregion

        #region Public Methods
        public void SetFilmScreenings()
        {
            FilmOutlinables = new List<IFilmOutlinable> { };
            foreach (var screening in Film.FilmScreenings)
            {
                var screeningOutlinable = new ScreeningOutlinable(screening, ScreeningOutlinable.Level.FilmScreening);
                FilmOutlinables.Add(screeningOutlinable);
                screeningOutlinable.SetOverlappingScreenings();
            }
        }
        #endregion
    }
}
