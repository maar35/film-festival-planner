using System;

namespace PresentScreenings.TableView
{
    public class FriendFilmRating
    {
        #region Private Variables
        int _filmId;
        string _friend;
        FilmRating _rating;
        #endregion

        #region Properties
        public int FilmId => _filmId;
        public string Friend => _friend;
        public FilmRating Rating { get => _rating; set => _rating = value; }
        #endregion

        #region Constructors
        public FriendFilmRating(string friendFilmRatingText)
        {
            string[] fields = friendFilmRatingText.Split(';');
            string filmId = fields[0];
            _friend = fields[1];
            string rating = fields[2];

            _filmId = Int32.Parse(filmId);
            _rating = new FilmRating(rating);
        }

        public FriendFilmRating(int filmId, string friend, FilmRating rating)
        {
            _filmId = filmId;
            _friend = friend;
            _rating = rating;
        }
        #endregion

        #region Public Methods

        public static string WriteHeader()
        {
            return "filmid;friend;rating";
        }

        public static string Serialize(FriendFilmRating friendFilmRating)
        {
            string line = string.Join
                (
                    ";",
                    friendFilmRating._filmId.ToString(),
                    friendFilmRating._friend,
                    friendFilmRating._rating.ToString()
                );
            return line;
        }
        #endregion
    }
}
