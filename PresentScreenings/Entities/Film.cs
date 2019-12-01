using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Keeps information about a film and supports international sorting and personal rating.
    /// </summary>

    public class Film : ListStreamer, IFilmOutlinable
    {
        #region Public Members
        public enum FilmInfoStatus
        {
            Absent,
            UrlOnly,
            UrlError,
            ParseError,
            Complete
        }
        #endregion

        #region Private Members
        #endregion

        #region Properties
        public int FilmId { get; private set; }
        public string SortedTitle { get; private set; }
        public string Title { get; private set; }
        public string TitleLanguage { get; private set; }
        public string Section { get; private set; }
        public string Url { get; private set; }
        public FilmRating Rating => ViewController.GetFilmFanFilmRating(this, ScreeningInfo.Me);
        public WebUtility.MediumCatagory Catagory { get; private set; }
        public FilmInfoStatus InfoStatus { get => ViewController.GetFilmInfoStatus(FilmId); }
        public FilmRating MaxRating => ViewController.GetMaxRating(this);
        public List<IFilmOutlinable> FilmOutlinables { get; private set; } = new List<IFilmOutlinable> { };
        #endregion

        #region Constructors
        public Film() { }

        public Film(string filmText)
        {
            // Assign the fields of the input string.
            string[] fields = filmText.Split(';');
            string filmId = fields[0];
            SortedTitle = fields[1];
            Title = fields[2];
            TitleLanguage = fields[3];
            Section = fields[4];
            string catagory = fields[5];
            Url = fields[6];

            // Assign properties that need calculating.
            FilmId = Int32.Parse(filmId);
            Catagory = (WebUtility.MediumCatagory)Enum.Parse(typeof(WebUtility.MediumCatagory), catagory);
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return Title;
        }
        #endregion

        #region Interface Implementations
        bool IFilmOutlinable.ContainsFilmOutlinables()
        {
            return FilmOutlinables.Count > 0;
        }

        void IFilmOutlinable.SetTitle(NSTextField view)
        {
            view.StringValue = Title;
            view.LineBreakMode = NSLineBreakMode.TruncatingMiddle;
            view.Selectable = false;
        }

        void IFilmOutlinable.SetRating(NSTextField view)
        {
            view.StringValue = MaxRating.ToString();
        }

        public void SetGo(NSView view)
        {
            ScreeningsView.DisposeSubViews(view);
        }

        void IFilmOutlinable.SetInfo(NSTextField view)
        {
            view.StringValue = FilmInfo.InfoString(this);
            view.LineBreakMode = NSLineBreakMode.ByWordWrapping;
            view.BackgroundColor = NSColor.Clear;
            view.TextColor = NSColor.Text;
        }
        #endregion

        #region Public Methods
        public void SetScreenings()
        {
            var filmScreenings = ViewController.FilmScreenings(FilmId);
            if (FilmOutlinables.Count == 0)
            {
                FilmOutlinables.AddRange(filmScreenings);
            }
            foreach (var filmScreening in filmScreenings)
            {
                filmScreening.SetOverlappingScreenings();
            }
        }
        #endregion
    }
}
