import os
import numpy as np
import threading
import uuid
import warnings

warnings.filterwarnings('ignore')

from utils import read_video, save_video
from trackers import Tracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistance_Estimator

tasks = {}


def process_video(task_id, input_path, output_path, use_stubs=False):
    try:
        tasks[task_id]['stage'] = 'Reading video frames...'
        tasks[task_id]['progress'] = 5
        video_frames = read_video(input_path)
        tasks[task_id]['frame_count'] = len(video_frames)
        tasks[task_id]['progress'] = 10

        tasks[task_id]['stage'] = 'Detecting & tracking objects...'
        tasks[task_id]['progress'] = 15
        tracker = Tracker('models/best.pt')

        stub_track = 'stubs/track_stubs.pkl' if use_stubs else None
        tracks = tracker.get_object_tracks(
            video_frames,
            read_from_stub=use_stubs,
            stub_path=stub_track
        )
        tracker.add_position_to_tracks(tracks)
        tasks[task_id]['progress'] = 35

        tasks[task_id]['stage'] = 'Estimating camera movement...'
        tasks[task_id]['progress'] = 40
        camera_movement_estimator = CameraMovementEstimator(video_frames[0])

        stub_camera = 'stubs/camera_movement_stub.pkl' if use_stubs else None
        camera_movement_per_frame = camera_movement_estimator.get_camera_movement(
            video_frames,
            read_from_stub=use_stubs,
            stub_path=stub_camera
        )
        camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)
        tasks[task_id]['progress'] = 50

        tasks[task_id]['stage'] = 'Applying perspective transformation...'
        tasks[task_id]['progress'] = 55
        view_transformer = ViewTransformer()
        view_transformer.add_transformed_position_to_tracks(tracks)

        tasks[task_id]['stage'] = 'Interpolating ball positions...'
        tasks[task_id]['progress'] = 60
        tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])

        tasks[task_id]['stage'] = 'Calculating speed & distance...'
        tasks[task_id]['progress'] = 65
        speed_and_distance_estimator = SpeedAndDistance_Estimator()
        speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)

        tasks[task_id]['stage'] = 'Assigning teams by jersey color...'
        tasks[task_id]['progress'] = 70
        team_assigner = TeamAssigner()
        team_assigner.assign_team_color(video_frames[0], tracks['players'][0])

        for frame_num, player_track in enumerate(tracks['players']):
            for player_id, track in player_track.items():
                team = team_assigner.get_player_team(
                    video_frames[frame_num], track['bbox'], player_id
                )
                tracks['players'][frame_num][player_id]['team'] = team
                tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team]

        tasks[task_id]['stage'] = 'Computing ball possession...'
        tasks[task_id]['progress'] = 75
        player_assigner = PlayerBallAssigner()
        team_ball_control = []
        for frame_num, player_track in enumerate(tracks['players']):
            ball_bbox = tracks['ball'][frame_num][1]['bbox']
            assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

            if assigned_player != -1:
                tracks['players'][frame_num][assigned_player]['has_ball'] = True
                team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'])
            else:
                team_ball_control.append(team_ball_control[-1] if team_ball_control else 1)
        team_ball_control = np.array(team_ball_control)

        tasks[task_id]['stage'] = 'Rendering annotated video...'
        tasks[task_id]['progress'] = 80
        output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)

        tasks[task_id]['progress'] = 85
        output_video_frames = camera_movement_estimator.draw_camera_movement(
            output_video_frames, camera_movement_per_frame
        )

        tasks[task_id]['progress'] = 90
        speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)

        tasks[task_id]['stage'] = 'Saving output video...'
        tasks[task_id]['progress'] = 95
        save_video(output_video_frames, output_path)

        tasks[task_id]['stage'] = 'Analysis complete!'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['status'] = 'complete'

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)
        import traceback
        print(f"Error processing task {task_id}: {traceback.format_exc()}")


def start_processing(input_path, output_path, use_stubs=False):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'status': 'processing',
        'progress': 0,
        'stage': 'Initializing pipeline...',
        'frame_count': 0,
        'output_path': output_path,
        'error': None
    }

    thread = threading.Thread(
        target=process_video,
        args=(task_id, input_path, output_path, use_stubs),
        daemon=True
    )
    thread.start()

    return task_id
