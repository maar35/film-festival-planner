using System;
using System.Collections.Generic;
using System.IO;

namespace PresentScreenings.TableView
{
	/// <summary>
    /// List reader, read a file and return is list of generic objects.
    /// </summary>

    public abstract class ListReader<T> where T : class, new()
    {
        #region Virtual Methods
        public virtual bool ListFileIsMandatory()
        {
            return true;
        }
        public virtual bool ListFileHasHeader()
        {
            return true;
        }
        #endregion

        #region Public Methods
        public List<T> ReadListFromFile(string fileName, Func<string, T> lineConstructor)
        {
            var resultList = new List<T> { };
			using (var streamReader = OpenStream(fileName))
			{
                if (streamReader != null)
                {
                    string line;
                    bool headerToBeSkipped = ListFileHasHeader();
                    while ((line = streamReader.ReadLine()) != null)
                    {
                        if (headerToBeSkipped)
                        {
                            headerToBeSkipped = false;
                            continue;
                        }
                        resultList.Add(lineConstructor(line));
                    }
                }
            }
			return resultList;
		}
		#endregion

		#region Private Methods
		private StreamReader OpenStream(string url)
		{
			FileStream fileStream;
			try
			{
                fileStream = new FileStream(url, FileMode.Open, FileAccess.Read);
			}
            catch (FileNotFoundException)
            {
                if (ListFileIsMandatory())
                {
                    throw new FileNotFoundException();
                }
                else
                {
                    return null;
                }
            }
            catch (Exception ex)
			{
				throw new Exception(string.Format("Read error, couldn't access file {0}", url), ex);
            }
			return new StreamReader(fileStream);
		}
		#endregion
	}
}
