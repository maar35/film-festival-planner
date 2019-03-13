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
            UrlOnly,
            UrlError,
            ParseError,
            Complete
        }
        #endregion

        #region Private Members
        FilmRating _rating;
        #endregion

        #region Properties
        public int FilmId { get; private set; }
        public string SortedTitle { get; private set; }
        public string Title { get; private set; }
        public string TitleLanguage { get; private set; }
        public string Section { get; private set; }
        public string Url { get; private set; }
        public FilmRating Rating { get => _rating; set => _rating = value; }
        public WebUtility.MediumCatagory Catagory { get; private set; }
        public FilmInfoStatus InfoStatus { get => ViewController.GetFilmInfo(FilmId).InfoStatus; }
        //{
        //get => _filmInfoStatus;
        //set
        //{
        //    var filmInfo = ViewController.GetFilmInfo(FilmId);
        //    if (filmInfo != null)
        //    {
        //        filmInfo.InfoStatus = value;
        //    }
        //    else
        //    {
        //        filmInfo = new FilmInfo(FilmId, InfoStatus, Catagory, Url, string.Empty, string.Empty)
        //        {
        //            InfoStatus = value
        //        };
        //        ScreeningsPlan.FilmInfos.Add(filmInfo);
        //        //ViewController.AddFilmInfo(filmInfo);
        //    }
        //    _filmInfoStatus = filmInfo.InfoStatus;
        //}
        //}
        #endregion

        #region Constructors
        public Film(string filmText)
        {
            string[] fields = filmText.Split(';');
            string filmId = fields[0];
            SortedTitle = fields[1];
            Title = fields[2];
            TitleLanguage = fields[3];
            Section = fields[4];
            string catagory = fields[5];
            Url = fields[6];
            string rating = fields[7];
            string filmInfoStatus = fields[8];

            FilmId = Int32.Parse(filmId);
            _rating = new FilmRating(rating);
            Catagory = (WebUtility.MediumCatagory)Enum.Parse(typeof(WebUtility.MediumCatagory), catagory);

            //// Temporary while moving InfoStatus from class Film to FilmInfo.
            // Get the downloaded film info if present.
            var filmInfo = ViewController.GetFilmInfo(FilmId);
            //InfoStatus = filmInfo != null ? filmInfo.InfoStatus : FilmInfoStatus.Absent;
            //if (filmInfo != null)
            //{
            //    InfoStatus = filmInfo.InfoStatus;
            //    //InfoStatus = FilmInfoStatus.Complete;
            //}
            //else
            //{
            //    var infoStatus = (FilmInfoStatus)Enum.Parse(typeof(FilmInfoStatus), filmInfoStatus);
            //    var dummy = new FilmInfo(FilmId, infoStatus);
            //}
            if (filmInfo == null)
            {
                var infoStatus = (FilmInfoStatus)Enum.Parse(typeof(FilmInfoStatus), filmInfoStatus);
                var dummy = new FilmInfo(FilmId, infoStatus);
            }

        }
        #endregion

        #region Public Methods
        public static string WriteHeader()
        {
            return "filmid;sort;title;titlelanguage;section;mediacatagory;url;rating;filminfostatus";
        }

        public static string Serialize(Film film)
        {
            string line = string.Join(";",
                film.FilmId, film.SortedTitle, film.Title, film.TitleLanguage, film.Section, film.Catagory, film.Url, film._rating, film.InfoStatus.ToString()
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