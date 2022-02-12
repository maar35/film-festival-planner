using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Keeps information about a film and supports international sorting and personal rating.
    /// </summary>

    public class Film : ListStreamer, IComparable
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
        private Subsection Subsection { get; set; }
        public string SubsectionName => Subsection == null ? string.Empty : Subsection.Name;
        public NSColor SubsectionColor => Subsection == null ? NSColor.Black : Subsection.Section.Color;
        public TimeSpan Duration { get; private set; }
        public string DurationFormat => "hh\\:mm";
        public string DurationString => Duration.ToString(DurationFormat);
        public string MinutesString => Duration.TotalMinutes + "′";
        public string Url { get; private set; }
        public List<Screening> FilmScreenings => ViewController.FilmScreenings(FilmId);
        public FilmRating Rating => ViewController.GetFilmFanFilmRating(this, ScreeningInfo.Me);
        public WebUtility.MediumCategory Category { get; private set; }
        public FilmInfoStatus InfoStatus => ViewController.GetFilmInfoStatus(FilmId);
        public FilmRating MaxRating => ViewController.GetMaxRating(this);
        #endregion

        #region Cached Properties
        private FilmInfo _filmInfo = null;
        public FilmInfo FilmInfo
        {
            get
            {
                if (_filmInfo == null)
                    _filmInfo = ViewController.GetFilmInfo(FilmId);
                return _filmInfo;
            }
        }
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
            string subsectionIdStr = fields[5];
            string duration = fields[6];
            string category = fields[7];
            Url = fields[8];

            // Assign properties that need calculating.
            SequenceNumber = int.Parse(sequenceNumber);
            FilmId = int.Parse(filmId);
            int? subsectionId = int.TryParse(subsectionIdStr, out int outcome) ? (int?)outcome : null;
            Subsection = ViewController.GetSubsection(subsectionId);
            int minutes = int.Parse(duration.TrimEnd('′'));
            Duration = new TimeSpan(0, minutes, 0);
            Category = (WebUtility.MediumCategory)Enum.Parse(typeof(WebUtility.MediumCategory), category);

            // Get Film Info.
            if (FilmInfo == null)
            {
                ScreeningsPlan.FilmInfos.Add(new FilmInfo(FilmId, FilmInfoStatus.Absent, "", ""));
                _filmInfo = null;
            }
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return Title;
        }

        public override string WriteHeader()
        {
            return "title;duration;maarten;adrienne;genre;url;description";
        }

        public override string Serialize()
        {
            string line = string.Empty;
            List<string> fields = new List<string> { };

            fields.Add(ToString());
            fields.Add(DurationString);
            fields.Add(Rating.ToString());
            fields.Add(ViewController.GetFilmFanFilmRating(this, "Adrienne").ToString());
            fields.Add(FilmInfo.GetGenreDescription());
            fields.Add(FilmInfo.Url);
            fields.Add(FilmInfo.FilmDescription.Replace("\n", " "));

            return string.Join(";", fields);
        }
        #endregion

        #region Interface Implementations
        public int CompareTo(object obj)
        {
            return SequenceNumber.CompareTo(((Film)obj).SequenceNumber);
        }
        #endregion
    }
}
