from src.preprocess.preprocessor import SeqProcessor
from src.config.static_config import StaticConfig
from src.train.bidirectional_lstm_model import Bidirectional_LSTM_Model
import pandas as pd
import pickle
from src.utils.utils import list_files_under_folder, create_folder, is_dir_exist

class Predictor(object):
    def __init__(self):
        self.x_test = None
        self.global_config = StaticConfig()
        self.preprocessor = None

    def load_data(self, test_data_file_path, preprocessor_folder_path):
        self.x_test = pd.read_csv(test_data_file_path)
        tokenizer = pickle.load(open('{}/{}'.format(preprocessor_folder_path, self.global_config.tokenizer_save_name)
                , "rb"))
        self.preprocessor = SeqProcessor(tokenizer)

    def predict(self, empty_model_object, models_parent_folder_path, prediction_save_path, submission=False
                , load_sample_submission_file_path=None):
        print("##################### predict starts ########################")
        if not submission:
            original_labels = self.preprocessor.extract_y(self.x_test)
            create_folder(prediction_save_path)
            original_labels.to_csv("{}/{}".format(prediction_save_path, self.global_config.original_label_file_name))
        predict = None

        for folder_name in self.global_config.labels:
            print("processing ",folder_name)
            x_test = self.preprocessor.preprocess_train(self.x_test, submission)
            predict_for_model = self.predict_for_model_under_same_folder(empty_model_object, models_parent_folder_path, folder_name, prediction_save_path, x_test[0])
            if predict_for_model is None:
                continue
            if predict is None:
                predict = predict_for_model
            else:
                if self.global_config.enable_rebalancing_sampling:
                    predict[folder_name] = predict_for_model[folder_name]
                else:
                    predict += predict_for_model
        if not self.global_config.enable_rebalancing_sampling:
            predict = predict/len(self.global_config.labels)

        if submission:
            sample = pd.read_csv(load_sample_submission_file_path)
            sample[self.global_config.labels] = predict
            sample.to_csv("{}/{}".format(prediction_save_path, self.global_config.ensembled_submission_file_name))
        else:
            predict.to_csv("{}/{}".format(prediction_save_path, self.global_config.ensembled_predict_file_name))
        print("##################### predict ends ########################")

    def predict_for_model_under_same_folder(self, empty_model_object, models_folder,folder_name, prediction_save_path, x_test):
        model_path = "{}/{}".format(models_folder, folder_name)
        print('predict_for_model_under_same_folder model_path', model_path)
        if not is_dir_exist(model_path):
            return None
        model_names = list_files_under_folder(model_path)
        y_test_list = []
        model_folder = prediction_save_path + "/" + folder_name
        create_folder(model_folder)
        for model_name in model_names:
            one_model_path = model_path+"/"+model_name
            empty_model_object.load_weights(one_model_path)
            y_test = empty_model_object.predict(x_test)

            save_path_for_one = model_folder +"/"+model_name+"_"+self.global_config.predict_save_name
            pd.DataFrame(y_test,columns=self.global_config.labels).to_csv(save_path_for_one)
            y_test_list.append(y_test)
            if not self.global_config.enable_rebalancing_sampling:
                break
        average_y_test = y_test_list[0]
        if self.global_config.enable_rebalancing_sampling:
            average_y_test = None
            for y_test in y_test_list:
                if average_y_test is None:
                    average_y_test = y_test
                else:
                    average_y_test += y_test
            average_y_test = average_y_test*1.0/len(y_test_list)
        save_path_for_average = model_folder +"/"+self.global_config.average_predict_save_name
        average_df = pd.DataFrame(average_y_test, columns = self.global_config.labels)
        average_df.to_csv(save_path_for_average)
        return average_df




if __name__ == '__main__':
    predictor = Predictor()
    predictor.load_data('./preprocessing_wrapper_demo_output/test.csv', "./preprocessing_wrapper_demo_output/")
    predictor.predict(Bidirectional_LSTM_Model().get_model(), './training_demo_output','./predict_demo_output')
