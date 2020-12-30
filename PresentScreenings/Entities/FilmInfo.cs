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
        #region Public Structures.
        public struct ScreenedFilm
        {
            public int ScreenedFilmId;
            public string Title;
            public string Description;
        }
        #endregion

        #region Properties
        public int FilmId { get; }
        public string FilmDescription { get; private set; }
        public string FilmArticle { get; private set; }
        public int? CombinationProgramId { get; private set; }
        public List<ScreenedFilm> ScreenedFilms { get; private set; }
        public WebUtility.MediumCategory MediumCategory => ViewController.GetFilmById(FilmId).Category;
        public string Url => ViewController.GetFilmById(FilmId).Url;
        public Film.FilmInfoStatus InfoStatus { get; }
        #endregion

        #region Constructors
        public FilmInfo(int filmId, Film.FilmInfoStatus infoStatus, string description, string article, int? combinationId)
        {
            FilmId = filmId;
            InfoStatus = infoStatus;
            FilmDescription = description;
            FilmArticle = article;
            CombinationProgramId = combinationId;
            ScreenedFilms = new List<ScreenedFilm> { };
        }
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
                string ScreenedFilmText(ScreenedFilm screenedFilm)
                {
                    Film film = ViewController.GetFilmById(screenedFilm.ScreenedFilmId);
                    string titleText = $"{screenedFilm.Title} ({film.MinutesString}) - {film.MaxRating}";
                    return titleText + Environment.NewLine + WebUtility.HtmlToText(screenedFilm.Description);
                }
                string header = "Screened films";
                if (!isCombinationProgram())
                {
                    int CombinationId;
                    try
                    {
                        CombinationId = (int)CombinationProgramId;
                        header = $"Also screened in {ViewController.GetFilmById(CombinationId)}:";
                    }
                    catch (InvalidOperationException) { }
                }
                builder.AppendLine(Environment.NewLine + header);
                var space = Environment.NewLine + Environment.NewLine;
                builder.AppendLine(string.Join(space, ScreenedFilms.Select(f => ScreenedFilmText(f))));
            }
            return builder.ToString();
        }
        #endregion

        #region Public Methods
        public void AddScreenedFilm(int filmid, string title, string description)
        {
            var screenedFilm = new ScreenedFilm();
            screenedFilm.ScreenedFilmId = filmid;
            screenedFilm.Title = title;
            screenedFilm.Description = description;
            ScreenedFilms.Add(screenedFilm);
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
                    (string)el.Attribute("CombinationProgramId"),
                    from s in el.Element("ScreenedFilms").Elements("ScreenedFilm")
                    select
                    (
                        (string)s.Attribute("ScreenedFilmId"),
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
                    filmInfoElement.Item4,
                    int.TryParse(filmInfoElement.Item5, out int outcome) ? (int?)outcome : null
                );
                foreach (var screenedFilmAttribute in filmInfoElement.Item6)
                {
                    int filmid = Int32.Parse(screenedFilmAttribute.Item1);
                    var title = screenedFilmAttribute.Item2;
                    var description = screenedFilmAttribute.Item3;
                    filmInfo.AddScreenedFilm(filmid, title, description);
                }
                filmInfos.Add(filmInfo);
            }
            return filmInfos;
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

        private bool isCombinationProgram()
        {
            return MediumCategory == WebUtility.MediumCategory.CombinedProgrammes;
        }
        #endregion
    }
}
