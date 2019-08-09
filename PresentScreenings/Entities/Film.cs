using System;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Keeps information about a film and supports international sorting and personal rating.
    /// </summary>

    public class Film
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
        public int FilmId { get; private set; }
        public string SortedTitle { get; private set; }
        public string Title { get; private set; }
        public string TitleLanguage { get; private set; }
        public string Section { get; private set; }
        public string Url { get; private set; }
        public FilmRating Rating => ViewController.GetFilmFanFilmRating(this, ScreeningInfo.Me);
        public WebUtility.MediumCatagory Catagory { get; private set; }
        public FilmInfoStatus InfoStatus { get => ViewController.GetFilmInfo(FilmId).InfoStatus; }
        #endregion

        #region Constructors
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

        #region Public Methods
        public static string WriteHeader()
        {
            return "filmid;sort;title;titlelanguage;section;mediacatagory;url";
        }

        public static string Serialize(Film film)
        {
            string line = string.Join(";",
                film.FilmId, film.SortedTitle, film.Title, film.TitleLanguage, film.Section, film.Catagory, film.Url
            );
            return line;
        }

        public override string ToString()
        {
            return Title;
        }
        #endregion
    }
}
