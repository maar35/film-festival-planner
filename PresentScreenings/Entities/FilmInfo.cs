using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Xml.Linq;

namespace PresentScreenings.TableView
{
    public class FilmInfo
    {
        #region Private Members
        private Film.FilmInfoStatus _infoStatus;
        #endregion

        #region Properties
        public int FilmId { get; }
        public string FilmDescription { get; private set; }
        public string FilmArticle { get; private set; }
        public struct ScreenedFilm
        {
            public string Title;
            public string Description;
        }
        public List<ScreenedFilm> ScreenedFilms { get; private set; }
        public WebUtility.MediumCategory MediumCategory { get => ViewController.GetFilmById(FilmId).Category; }
        public string Url { get => ViewController.GetFilmById(FilmId).Url; }
        public Film.FilmInfoStatus InfoStatus { get => _infoStatus; set => SetFilmInfoStatus(value); }
        #endregion

        #region Constructors
        public FilmInfo(int filmId, Film.FilmInfoStatus infoStatus, string description, string article)
        {
            FilmId = filmId;
            _infoStatus = infoStatus;
            FilmDescription = description;
            FilmArticle = article;
            ScreenedFilms = new List<ScreenedFilm> { };
        }

        public FilmInfo(int filmId, Film.FilmInfoStatus infoStatus)
            : this(filmId, infoStatus, string.Empty, string.Empty) { }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            var builder = new StringBuilder(Url + Environment.NewLine);
            if (FilmDescription != string.Empty)
            {
                builder.AppendLine(Environment.NewLine + "Description");
                builder.AppendLine(WebUtility.HtmlToText(FilmDescription));
            }
            if (FilmArticle != string.Empty)
            {
                builder.AppendLine(Environment.NewLine + "Article");
                builder.AppendLine(WebUtility.HtmlToText(FilmArticle));
            }
            if (ScreenedFilms.Count > 0)
            {
                builder.AppendLine(Environment.NewLine + "Screened films");
                var space = Environment.NewLine + Environment.NewLine;
                builder.AppendLine(string.Join(space, ScreenedFilms.Select(f => f.Title + Environment.NewLine + WebUtility.HtmlToText(f.Description))));
            }
            return builder.ToString();
        }
        #endregion

        #region Public Methods
        public void AddScreenedFilm(string title, string description)
        {
            var screenedFilm = new ScreenedFilm();
            screenedFilm.Title = title;
            screenedFilm.Description = description;
            ScreenedFilms.Add(screenedFilm);
        }

        public static void AddNewFilmInfo(int filmId, Film.FilmInfoStatus infoStatus)
        {
            CheckAddToFilmInfos(new FilmInfo(filmId, infoStatus));
        }

        public static void CheckAddToFilmInfos(FilmInfo filmInfo)
        {
            var filmInfos = ScreeningsPlan.FilmInfos;
            var count = filmInfos.Count(i => i.FilmId == filmInfo.FilmId);
            if (count > 0)
            {
                filmInfos.Remove(filmInfos.First(i => i.FilmId == filmInfo.FilmId));
            }
            filmInfos.Add(filmInfo);
        }

        public static List<FilmInfo> LoadFilmInfoFromXml(string path)
        {
            var filmInfos = new List<FilmInfo> { };
            XElement root;
            try
            {
                root = XElement.Load(path);
            }
            catch (FileNotFoundException)
            {
                return filmInfos;
            }
            catch (System.Exception)
            {
                return filmInfos;
            }
            var filmInfoElements =
                from el in root.Elements("FilmInfo")
                select
                (
                    (int)el.Attribute("FilmId"),
                    (string)el.Attribute("InfoStatus"),
                    (string)el.Attribute("FilmDescription"),
                    (string)el.Attribute("FilmArticle"),
                    from s in el.Element("ScreenedFilms").Elements("ScreenedFilm")
                    select
                    (
                        (string)s.Attribute("Title"),
                        (string)s.Attribute("Description")
                    )
                );
            foreach (var filmInfoElement in filmInfoElements)
            {
                var filmInfo = new FilmInfo
                (
                    filmInfoElement.Item1,
                    StringToFilmInfoStatus(filmInfoElement.Item2),
                    filmInfoElement.Item3,
                    filmInfoElement.Item4
                );
                foreach (var screenedFilmAttribute in filmInfoElement.Item5)
                {
                    var title = screenedFilmAttribute.Item1;
                    var description = screenedFilmAttribute.Item2;
                    filmInfo.AddScreenedFilm(title, description);
                }
                filmInfos.Add(filmInfo);
            }
            return filmInfos;
        }

        public static void SaveFilmInfoAsXml(List<FilmInfo> filmInfos, string path)
        {
            var xml = new XElement
            (
                "FilmInfos",
                from filmInfo in filmInfos
                select new XElement
                (
                    "FilmInfo",
                    new XAttribute("FilmId", filmInfo.FilmId),
                    new XAttribute("InfoStatus", filmInfo.InfoStatus),
                    new XAttribute("FilmDescription", filmInfo.FilmDescription),
                    new XAttribute("FilmArticle", filmInfo.FilmArticle),
                    new XElement
                    (
                        "ScreenedFilms",
                        from screenedFilm in filmInfo.ScreenedFilms
                        select new XElement
                        (
                            "ScreenedFilm",
                            new XAttribute("Title", screenedFilm.Title),
                            new XAttribute("Description", screenedFilm.Description)
                        )
                    )
                )
            );
            xml.Save(path);
        }

        public static string InfoString(Film film)
        {
            var filmInfo = ViewController.GetFilmInfo(film.FilmId);
            if (filmInfo == null)
            {
                return string.Empty;
            }
            string text = filmInfo.FilmDescription;
            if (text.Length == 0)
            {
                text = filmInfo.FilmArticle;
            }
            return Screening.HtmlDecode(text);
        }
        #endregion

        #region Private Methods
        private static Film.FilmInfoStatus StringToFilmInfoStatus(string name)
        {
            try
            {
                return (Film.FilmInfoStatus)Enum.Parse(typeof(Film.FilmInfoStatus), name);
            }
            catch
            {
                throw new IllegalFilmInfoCategoryException($"'{name}' is not a valid FilmInfoCategory");
            }
        }

        private void SetFilmInfoStatus(Film.FilmInfoStatus status)
        {
            _infoStatus = status;
            CheckAddToFilmInfos(this);
        }
        #endregion
    }
}
