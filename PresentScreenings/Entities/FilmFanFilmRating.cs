using System;

namespace PresentScreenings.TableView
{
    public class FilmFanFilmRating : ListReader<FilmFanFilmRating>, ICanWriteList
    {
        #region Properties
        public int FilmId { get; }
        public string FilmFan { get; }
        public FilmRating Rating { get; set; }
        #endregion

        #region Constructors
        public FilmFanFilmRating() { }

        public FilmFanFilmRating(string filmFanFilmRatingText)
        {
            string[] fields = filmFanFilmRatingText.Split(';');
            string filmId = fields[0];
            FilmFan = fields[1];
            string rating = fields[2];

            FilmId = Int32.Parse(filmId);
            Rating = new FilmRating(rating);
        }

        public FilmFanFilmRating(int filmId, string filmFan, FilmRating rating)
        {
            FilmId = filmId;
            FilmFan = filmFan;
            Rating = rating;
        }
        #endregion

        #region Override Methods
        public override bool ListFileIsMandatory()
        {
            return false;
        }
        #endregion

        #region Interface Implementations
        string ICanWriteList.Serialize()
        {
            return string.Join(";", FilmId.ToString(), FilmFan, Rating.ToString());
        }
        #endregion

        #region Public Methods
        public static string WriteHeader()
        {
            return "filmid;filmfan;rating";
        }
        #endregion
    }
}
