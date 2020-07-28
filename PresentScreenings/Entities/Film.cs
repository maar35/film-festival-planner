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

        #region Properties
        public int SequenceNumber { get; private set; }
        public int FilmId { get; private set; }
        public string SortedTitle { get; private set; }
        public string Title { get; private set; }
        public string TitleLanguage { get; private set; }
        public string Section { get; private set; }
        public TimeSpan Duration { get; private set; }
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
            string sequenceNumber = fields[0];
            string filmId = fields[1];
            SortedTitle = fields[2];
            Title = fields[3];
            TitleLanguage = fields[4];
            Section = fields[5];
            string duration = fields[6];
            string catagory = fields[7];
            Url = fields[8];

            // Assign properties that need calculating.
            SequenceNumber = int.Parse(sequenceNumber);
            FilmId = int.Parse(filmId);
            int minutes = int.Parse(duration.TrimEnd('′'));
            Duration = new TimeSpan(0, minutes, 0);
            Catagory = (WebUtility.MediumCatagory)Enum.Parse(typeof(WebUtility.MediumCatagory), catagory);
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return Title;
        }

        public override string WriteHeader()
        {
            return "title;duration;maarten;adrienne;url;description";
        }

        public override string Serialize()
        {
            string line = string.Empty;
            List<string> fields = new List<string> { };

            fields.Add(ToString());
            fields.Add(Duration.ToString(Screening._durationFormat));
            fields.Add(Rating.ToString());
            fields.Add(ViewController.GetFilmFanFilmRating(this, "Adrienne").ToString());
            var filmInfoList = ScreeningsPlan.FilmInfos.Where(i => i.FilmId == FilmId);
            var filmInfo = filmInfoList.Count() == 1 ? filmInfoList.First() : null;
            fields.Add(filmInfo != null ? filmInfo.Url : "");
            fields.Add(filmInfo != null ? Screening.HtmlDecode(filmInfo.FilmDescription) : "");

            return string.Join(";", fields);
        }
        #endregion

        #region Interface Implementations
        bool IFilmOutlinable.ContainsFilmOutlinables()
        {
            return FilmOutlinables.Count > 0;
        }

        void IFilmOutlinable.SetTitle(NSTextField view)
        {
            view.StringValue = Duration.ToString("hh\\:mm") + " - " + Title;
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
