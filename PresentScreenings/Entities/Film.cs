using System;
using System.Collections.Generic;
using System.Linq;

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
            UrlError,
            ParseError,
            Complete
        }
        #endregion

        #region Private Members
        int _filmId;
        string _sortedTitle;
        string _title;
        string _titleLanguage;
        string _section;
        FilmRating _rating;
        FilmInfoStatus _filmInfoStatus;
        #endregion

        #region Properties
        public int FilmId => _filmId;
        public string Title => _title;
        public string SortedTitle => _sortedTitle;
        public string Section => _section;
        public FilmRating Rating { get => _rating; set => _rating = value; }
        public FilmInfoStatus InfoStatus { get => _filmInfoStatus; set => _filmInfoStatus = value; }
        #endregion

        #region Constructors
        public Film(string filmText)
        {
            string[] fields = filmText.Split(';');
            string filmId = fields[0];
            _sortedTitle = fields[1];
            _title = fields[2];
            _titleLanguage = fields[3];
            _section = fields[4];
            string rating = fields[5];
            string filmInfoStatus = fields[6];

            _filmId = Int32.Parse(filmId);
            _rating = new FilmRating(rating);
            _filmInfoStatus = (FilmInfoStatus)Enum.Parse(typeof(FilmInfoStatus), filmInfoStatus);
        }
        #endregion

        #region Public Methods
        public static string WriteHeader()
        {
            return "filmid;sort;title;titlelanguage;section;rating;filminfostatus";
        }

        public static string Serialize(Film film)
        {
            string line = string.Join(";",
                film._filmId, film._sortedTitle, film._title, film._titleLanguage, film._section, film._rating, film._filmInfoStatus.ToString()
            );
            return line;
        }

        public override string ToString()
        {
            return _title;
        }
        #endregion
    }
}