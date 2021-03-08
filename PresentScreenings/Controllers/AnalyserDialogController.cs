// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;
using PresentScreenings.TableView.TableClasses;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Analyser dialog controller, manages a dialog wich displays high rated
    /// films in an outline view, allowing to expand to screenings and
    /// overlapping screenings.
    /// </summary>

    public partial class AnalyserDialogController : NSViewController, IScreeningProvider
	{
        #region Private Variables
        private ViewController _presentor;
        private FilmOutlineDataSource _dataSource;
        #endregion

        #region Constructors
        public AnalyserDialogController (IntPtr handle) : base (handle)
		{
        }
        #endregion

        #region Application Access
        private static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public NSOutlineView FilmOutlineView => _filmOutlineView;
        #endregion

        #region Interface Implementations
        Film IScreeningProvider.CurrentFilm => GetSelectedFilm();
        Screening IScreeningProvider.CurrentScreening => App.Controller.CurrentScreening;
        List<Screening> IScreeningProvider.Screenings => GetFilmScreenings();
        #endregion

        #region Override Methods
        public override void ViewDidLoad()
        {
            base.ViewDidLoad();

            // Initialize the presentor.
            _presentor = App.Controller;

            // Tell the app delegate we're alive.
            App.AnalyserDialogController = this;

            // Set the GoToScreening function for screenings.
            Screening.GoToScreening = App.NavigateFilmScreening;

            // Create data source and populate.
            _dataSource = new FilmOutlineDataSource();

            // Create the list of films.
            var films = new List<Film> { };
            var highRatedFilms = ScreeningsPlan.Films.Where(f => FilterHighRatedFilms(f));
            foreach (var highRatedFilm in highRatedFilms)
            {
                var screenings = highRatedFilm.FilmScreenings;
                if (screenings.Count == 0)
                {
                    continue;
                }
                if (!screenings.Exists(s => s.AutomaticallyPlanned) && !screenings.Exists(s => s.IAttend))
                {
                    films.Add(highRatedFilm);
                }
            }

            // Add the films to the outline data source.
            var sortedFilms = films.OrderByDescending(f => f.MaxRating).ThenBy(f => f.SequenceNumber);
            foreach (var film in sortedFilms)
            {
                film.SetScreenings();
                _dataSource.FilmOutlinables.Add(film);
            }

            // Populate the outline.
            _filmOutlineView.DataSource = _dataSource;
            _filmOutlineView.Delegate = new FilmOutlineDelegate(_dataSource, this);
            _filmOutlineView.AllowsColumnSelection = false;
            _filmOutlineView.AllowsEmptySelection = true;
        }

        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Inactivate screenings view actions.
            _presentor.RunningPopupsCount++;
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate we're gone.
            App.AnalyserDialogController = null;

            // Tell the main view controller we're gone.
            _presentor.RunningPopupsCount--;
        }
        #endregion

        #region Public Methods
        public bool OneItemSelected()
        {
            return _filmOutlineView.SelectedRowCount == 1;
        }

        public IFilmOutlinable GetSelectedItem()
        {
            if (OneItemSelected())
            {
                var row = _filmOutlineView.SelectedRow;
                var item = _filmOutlineView.ItemAtRow(row);
                return (IFilmOutlinable)item;
            }
            return null;
        }

        public Film GetSelectedFilm()
        {
            var filmOutlinable = GetSelectedItem();
            if (filmOutlinable == null)
            {
                return null;
            }
            if (filmOutlinable is Film film)
            {
                return film;
            }
            if (filmOutlinable is Screening screening)
            {
                return screening.Film;
            }
            var level = (FilmOutlineLevel)filmOutlinable;
            switch (level.OutlineLevel)
            {
                case FilmOutlineLevel.Level.Film:
                    break;
                case FilmOutlineLevel.Level.FilmScreening:
                    break;
                case FilmOutlineLevel.Level.OverlappingScreening:
                    return ((Screening)level.FilmOutlinable).Film;
            }
            return null;
        }

        public List<Screening> GetFilmScreenings()
        {
            var film = GetSelectedFilm();
            if (film != null)
            {
                return film.FilmScreenings;
            }
            return new List<Screening> { };
        }

        public static bool FilterHighRatedFilms(Film film)
        {
            return film.MaxRating.IsGreaterOrEqual(FilmRating.LowestSuperRating);
        }

        public void CloseDialog()
        {
            _presentor.DismissViewController(this);
        }
        #endregion
    }
}
